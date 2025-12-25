"""
RSS Feed Collector Module
Collects articles from RSS/Atom feeds defined in config/sources.yaml
"""

import feedparser
import hashlib
import logging
import time
from datetime import datetime
from typing import Generator
from pathlib import Path

import requests
import yaml
from dateutil import parser as date_parser

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
    
    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                       'utm_content', 'fbclid', 'gclid', 'ref', 'source']
    
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url)
    
    # Lowercase domain and remove www
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Filter out tracking parameters
    query_params = parse_qs(parsed.query)
    filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
    new_query = urlencode(filtered_params, doseq=True)
    
    # Remove trailing slash from path
    path = parsed.path.rstrip('/')
    
    # Reconstruct URL
    normalized = urlunparse((
        parsed.scheme,
        domain,
        path,
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return normalized


def get_url_hash(url: str) -> str:
    """Generate hash from normalized URL"""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_content_hash(title: str, published_at: str) -> str:
    """Generate fallback hash from title + date"""
    content = f"{title.lower().strip()}|{published_at[:10] if published_at else ''}"
    return hashlib.sha256(content.encode()).hexdigest()


def parse_date(date_str: str) -> str:
    """Parse various date formats to ISO 8601"""
    if not date_str:
        return datetime.utcnow().isoformat() + 'Z'
    
    try:
        dt = date_parser.parse(date_str)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return datetime.utcnow().isoformat() + 'Z'


def strip_html(text: str) -> str:
    """Remove HTML tags from text"""
    if not text:
        return ""
    
    import re
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def fetch_feed(url: str, timeout: int = 30, retries: int = 3) -> feedparser.FeedParserDict | None:
    """Fetch and parse RSS feed with retries"""
    headers = {
        'User-Agent': 'CivilEngineeringAI-NewsBot/1.0 (Academic Research)'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parsing error for {url}: {feed.bozo_exception}")
                return None
            
            return feed
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error for {url}: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    return None


def extract_entry(entry: dict, feed_name: str, feed_url: str) -> dict | None:
    """Extract article data from feed entry"""
    try:
        # Get link (try multiple fields)
        link = entry.get('link') or entry.get('id') or entry.get('guid', {}).get('href')
        if not link:
            return None
        
        # Get title
        title = entry.get('title', '')
        if not title:
            return None
        
        # Get published date
        published = entry.get('published') or entry.get('updated') or entry.get('created')
        published_at = parse_date(published)
        
        # Get description/snippet
        description = entry.get('description') or entry.get('summary') or ''
        snippet = strip_html(description)[:1000]  # Limit snippet length
        
        # Get author
        author = entry.get('author') or entry.get('author_detail', {}).get('name') or ''
        
        # Get categories/tags
        categories = [tag.get('term', '') for tag in entry.get('tags', [])]
        section = categories[0] if categories else ''
        
        # Generate unique ID
        url_hash = get_url_hash(link)
        content_hash = get_content_hash(title, published_at)
        
        return {
            'id': url_hash[:32],  # Use first 32 chars of hash as ID
            'title': title.strip(),
            'published_at': published_at,
            'source_name': feed_name,
            'source_type': 'RSS',
            'url': normalize_url(link),
            'full_text': snippet,  # RSS typically only has snippet, will be enriched later
            'author': author,
            'section': section,
            'language': 'en',
            'retrieved_at': datetime.utcnow().isoformat() + 'Z',
            'url_hash': url_hash,
            'content_hash': content_hash,
            'feed_url': feed_url
        }
        
    except Exception as e:
        logger.warning(f"Error extracting entry: {e}")
        return None


def collect_from_rss(max_articles: int = 300, seen_hashes: set = None) -> Generator[dict, None, None]:
    """
    Collect articles from all configured RSS feeds
    
    Args:
        max_articles: Maximum number of articles to collect
        seen_hashes: Set of already seen URL hashes for deduplication
    
    Yields:
        Article dictionaries
    """
    if seen_hashes is None:
        seen_hashes = set()
    
    config = load_config()
    feeds = config.get('RSS_FEEDS', [])
    
    collected = 0
    
    for feed_config in feeds:
        if collected >= max_articles:
            logger.info(f"Reached max articles limit ({max_articles})")
            break
        
        # Handle both dict and string formats
        if isinstance(feed_config, dict):
            url = feed_config.get('url')
            name = feed_config.get('name', url)
        else:
            url = feed_config
            name = url
        
        logger.info(f"Fetching RSS feed: {name}")
        
        feed = fetch_feed(url)
        if not feed:
            logger.warning(f"Failed to fetch feed: {url}")
            continue
        
        entries_collected = 0
        for entry in feed.entries:
            if collected >= max_articles:
                break
            
            article = extract_entry(entry, name, url)
            if not article:
                continue
            
            # Check for duplicates
            if article['url_hash'] in seen_hashes:
                logger.debug(f"Duplicate URL skipped: {article['url']}")
                continue
            
            if article['content_hash'] in seen_hashes:
                logger.debug(f"Duplicate content skipped: {article['title']}")
                continue
            
            # Add to seen hashes
            seen_hashes.add(article['url_hash'])
            seen_hashes.add(article['content_hash'])
            
            collected += 1
            entries_collected += 1
            yield article
        
        logger.info(f"Collected {entries_collected} articles from {name}")
        
        # Small delay between feeds to be polite
        time.sleep(0.5)
    
    logger.info(f"RSS collection complete. Total: {collected} articles")


def main():
    """Test RSS collector"""
    articles = list(collect_from_rss(max_articles=50))
    print(f"Collected {len(articles)} articles from RSS feeds")
    
    for article in articles[:5]:
        print(f"\n- {article['title'][:60]}...")
        print(f"  Source: {article['source_name']}")
        print(f"  URL: {article['url'][:80]}...")


if __name__ == "__main__":
    main()
