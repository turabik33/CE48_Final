"""
API Collector Module
Collects articles from news APIs (GNews, NewsAPI, Guardian, etc.)
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Generator
from pathlib import Path

import requests
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from sources.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication"""
    if not url:
        return ""
    
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                       'utm_content', 'fbclid', 'gclid', 'ref', 'source']
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    
    query_params = parse_qs(parsed.query)
    filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
    new_query = urlencode(filtered_params, doseq=True)
    
    path = parsed.path.rstrip('/')
    
    return urlunparse((parsed.scheme, domain, path, parsed.params, new_query, ''))


def get_url_hash(url: str) -> str:
    """Generate hash from normalized URL"""
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def get_content_hash(title: str, published_at: str) -> str:
    """Generate fallback hash from title + date"""
    content = f"{title.lower().strip()}|{published_at[:10] if published_at else ''}"
    return hashlib.sha256(content.encode()).hexdigest()


# ============================================================================
# GNEWS API
# ============================================================================

GNEWS_QUERIES = [
    '"civil engineering" AND (AI OR "artificial intelligence")',
    'construction AND (AI OR "machine learning" OR automation)',
    'infrastructure AND ("artificial intelligence" OR robotics)',
    '"structural engineering" AND (AI OR "deep learning")',
    'building AND ("computer vision" OR "predictive maintenance")',
    'BIM AND (AI OR "machine learning")',
    '"smart construction" OR "construction technology"',
    '"digital twin" AND (construction OR infrastructure)',
]


def collect_from_gnews(max_articles: int = 100, seen_hashes: set = None) -> Generator[dict, None, None]:
    """
    Collect articles from GNews API
    
    Args:
        max_articles: Maximum number of articles to collect
        seen_hashes: Set of already seen URL hashes for deduplication
    
    Yields:
        Article dictionaries
    """
    if seen_hashes is None:
        seen_hashes = set()
    
    api_key = os.environ.get('GNEWS_API_KEY')
    if not api_key:
        logger.warning("GNEWS_API_KEY not found in environment. Skipping GNews collection.")
        return
    
    base_url = "https://gnews.io/api/v4/search"
    collected = 0
    
    # Calculate date range (last 12 months)
    to_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    from_date = (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    for query in GNEWS_QUERIES:
        if collected >= max_articles:
            break
        
        logger.info(f"GNews query: {query[:50]}...")
        
        params = {
            'q': query,
            'lang': 'en',
            'max': 10,  # Free tier limit
            'from': from_date,
            'to': to_date,
            'sortby': 'relevance',
            'apikey': api_key
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get('articles', [])
            logger.info(f"GNews returned {len(articles)} articles for query")
            
            for article in articles:
                if collected >= max_articles:
                    break
                
                url = article.get('url', '')
                if not url:
                    continue
                
                url_hash = get_url_hash(url)
                if url_hash in seen_hashes:
                    continue
                
                title = article.get('title', '')
                published_at = article.get('publishedAt', datetime.utcnow().isoformat() + 'Z')
                content_hash = get_content_hash(title, published_at)
                
                if content_hash in seen_hashes:
                    continue
                
                seen_hashes.add(url_hash)
                seen_hashes.add(content_hash)
                
                yield {
                    'id': url_hash[:32],
                    'title': title,
                    'published_at': published_at,
                    'source_name': article.get('source', {}).get('name', 'Unknown'),
                    'source_type': 'API',
                    'url': normalize_url(url),
                    'full_text': article.get('content', article.get('description', '')),
                    'author': '',  # GNews doesn't provide author
                    'section': '',
                    'language': 'en',
                    'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                    'url_hash': url_hash,
                    'content_hash': content_hash,
                    'api_source': 'gnews'
                }
                
                collected += 1
            
            # Rate limiting - be nice to the API
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API error: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error in GNews collection: {e}")
            continue
    
    logger.info(f"GNews collection complete. Total: {collected} articles")


# ============================================================================
# NEWSAPI
# ============================================================================

def collect_from_newsapi(max_articles: int = 50, seen_hashes: set = None) -> Generator[dict, None, None]:
    """Collect articles from NewsAPI.org"""
    if seen_hashes is None:
        seen_hashes = set()
    
    api_key = os.environ.get('NEWSAPI_KEY')
    if not api_key:
        logger.info("NEWSAPI_KEY not found. Skipping NewsAPI collection.")
        return
    
    base_url = "https://newsapi.org/v2/everything"
    collected = 0
    
    queries = [
        'civil engineering AI',
        'construction technology',
        'infrastructure artificial intelligence',
        'smart building automation'
    ]
    
    from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    for query in queries:
        if collected >= max_articles:
            break
        
        logger.info(f"NewsAPI query: {query}")
        
        params = {
            'q': query,
            'language': 'en',
            'sortBy': 'relevance',
            'from': from_date,
            'pageSize': 20,
            'apiKey': api_key
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.warning(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                continue
            
            articles = data.get('articles', [])
            
            for article in articles:
                if collected >= max_articles:
                    break
                
                url = article.get('url', '')
                if not url:
                    continue
                
                url_hash = get_url_hash(url)
                if url_hash in seen_hashes:
                    continue
                
                title = article.get('title', '')
                published_at = article.get('publishedAt', datetime.utcnow().isoformat() + 'Z')
                content_hash = get_content_hash(title, published_at)
                
                if content_hash in seen_hashes:
                    continue
                
                seen_hashes.add(url_hash)
                seen_hashes.add(content_hash)
                
                yield {
                    'id': url_hash[:32],
                    'title': title,
                    'published_at': published_at,
                    'source_name': article.get('source', {}).get('name', 'Unknown'),
                    'source_type': 'API',
                    'url': normalize_url(url),
                    'full_text': article.get('content', article.get('description', '')),
                    'author': article.get('author', ''),
                    'section': '',
                    'language': 'en',
                    'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                    'url_hash': url_hash,
                    'content_hash': content_hash,
                    'api_source': 'newsapi'
                }
                
                collected += 1
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            continue
    
    logger.info(f"NewsAPI collection complete. Total: {collected} articles")


# ============================================================================
# GUARDIAN API
# ============================================================================

def collect_from_guardian(max_articles: int = 50, seen_hashes: set = None) -> Generator[dict, None, None]:
    """Collect articles from The Guardian Open Platform"""
    if seen_hashes is None:
        seen_hashes = set()
    
    api_key = os.environ.get('GUARDIAN_API_KEY')
    if not api_key:
        logger.info("GUARDIAN_API_KEY not found. Skipping Guardian collection.")
        return
    
    base_url = "https://content.guardianapis.com/search"
    collected = 0
    
    queries = ['civil engineering', 'construction technology', 'infrastructure AI']
    
    for query in queries:
        if collected >= max_articles:
            break
        
        logger.info(f"Guardian query: {query}")
        
        params = {
            'q': query,
            'api-key': api_key,
            'show-fields': 'headline,bodyText,byline,publication',
            'page-size': 20,
            'order-by': 'relevance'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('response', {}).get('results', [])
            
            for article in results:
                if collected >= max_articles:
                    break
                
                url = article.get('webUrl', '')
                if not url:
                    continue
                
                url_hash = get_url_hash(url)
                if url_hash in seen_hashes:
                    continue
                
                fields = article.get('fields', {})
                title = fields.get('headline', article.get('webTitle', ''))
                published_at = article.get('webPublicationDate', datetime.utcnow().isoformat() + 'Z')
                content_hash = get_content_hash(title, published_at)
                
                if content_hash in seen_hashes:
                    continue
                
                seen_hashes.add(url_hash)
                seen_hashes.add(content_hash)
                
                yield {
                    'id': url_hash[:32],
                    'title': title,
                    'published_at': published_at,
                    'source_name': 'The Guardian',
                    'source_type': 'API',
                    'url': normalize_url(url),
                    'full_text': fields.get('bodyText', '')[:5000],  # Limit text length
                    'author': fields.get('byline', ''),
                    'section': article.get('sectionName', ''),
                    'language': 'en',
                    'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                    'url_hash': url_hash,
                    'content_hash': content_hash,
                    'api_source': 'guardian'
                }
                
                collected += 1
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Guardian API error: {e}")
            continue
    
    logger.info(f"Guardian collection complete. Total: {collected} articles")


# ============================================================================
# MAIN API COLLECTOR
# ============================================================================

def collect_from_apis(max_articles: int = 250, seen_hashes: set = None) -> Generator[dict, None, None]:
    """
    Collect articles from all available APIs
    
    Args:
        max_articles: Maximum total articles to collect from all APIs
        seen_hashes: Set of already seen URL hashes for deduplication
    
    Yields:
        Article dictionaries
    """
    if seen_hashes is None:
        seen_hashes = set()
    
    collected = 0
    
    # Calculate quota per API
    gnews_quota = min(100, max_articles)
    remaining = max_articles - gnews_quota
    
    # GNews (primary)
    logger.info("Starting GNews collection...")
    for article in collect_from_gnews(gnews_quota, seen_hashes):
        yield article
        collected += 1
    
    if collected >= max_articles:
        return
    
    # NewsAPI (backup)
    remaining = max_articles - collected
    newsapi_quota = min(50, remaining // 2)
    
    logger.info("Starting NewsAPI collection...")
    for article in collect_from_newsapi(newsapi_quota, seen_hashes):
        yield article
        collected += 1
    
    if collected >= max_articles:
        return
    
    # Guardian (backup)
    remaining = max_articles - collected
    guardian_quota = min(50, remaining)
    
    logger.info("Starting Guardian collection...")
    for article in collect_from_guardian(guardian_quota, seen_hashes):
        yield article
        collected += 1
    
    logger.info(f"API collection complete. Total: {collected} articles")


def main():
    """Test API collector"""
    articles = list(collect_from_apis(max_articles=20))
    print(f"Collected {len(articles)} articles from APIs")
    
    for article in articles[:5]:
        print(f"\n- {article['title'][:60]}...")
        print(f"  Source: {article['source_name']} ({article.get('api_source', 'unknown')})")


if __name__ == "__main__":
    main()
