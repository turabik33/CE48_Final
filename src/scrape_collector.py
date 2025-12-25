"""
Web Scraping Collector Module
Scrapes articles from seed URLs with ethical rate limiting
"""

import hashlib
import logging
import random
import re
import time
from datetime import datetime
from typing import Generator, List
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                       'utm_content', 'fbclid', 'gclid', 'ref', 'source']
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace('www.', '') if parsed.netloc.lower().startswith('www.') else parsed.netloc.lower()
    query_params = parse_qs(parsed.query)
    filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
    new_query = urlencode(filtered_params, doseq=True)
    path = parsed.path.rstrip('/')
    return urlunparse((parsed.scheme, domain, path, parsed.params, new_query, ''))


def get_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def get_content_hash(title: str, published_at: str) -> str:
    content = f"{title.lower().strip()}|{published_at[:10] if published_at else ''}"
    return hashlib.sha256(content.encode()).hexdigest()


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def is_paywall_or_blocked(soup: BeautifulSoup, response: requests.Response) -> bool:
    if response.status_code in [402, 403]:
        return True
    paywall_indicators = ['paywall', 'subscription-required', 'subscriber-only', 'premium-content', 'members-only']
    html_text = str(soup).lower()
    for indicator in paywall_indicators:
        if soup.find(class_=re.compile(indicator, re.I)) or soup.find(id=re.compile(indicator, re.I)):
            return True
    return False


def get_page(url: str, timeout: int = 30):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser'), response
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None, None


def extract_generic(soup: BeautifulSoup, url: str) -> dict | None:
    try:
        # Find title - use attrs dict to avoid 'name' parameter conflict
        title_elem = soup.find('h1') or soup.find('meta', attrs={'property': 'og:title'})
        if not title_elem:
            return None
        title = title_elem.get('content', '') if title_elem.name == 'meta' else title_elem.get_text(strip=True)
        if not title or len(title) < 10:
            return None
        
        published_at = None
        date_elem = soup.find('time') or soup.find('meta', attrs={'property': 'article:published_time'})
        if date_elem:
            published_at = date_elem.get('datetime') or date_elem.get('content') or date_elem.get_text(strip=True)
        
        author = ''
        # Use attrs dict to avoid conflict with BeautifulSoup's 'name' parameter
        author_elem = soup.find('meta', attrs={'name': 'author'})
        if not author_elem:
            author_elem = soup.find(class_=re.compile('author|byline', re.I))
        if author_elem:
            author = author_elem.get('content', '') if author_elem.name == 'meta' else author_elem.get_text(strip=True)
        
        body = soup.find('article') or soup.find('div', class_=re.compile('article|content|body', re.I))
        full_text = ''
        if body:
            for unwanted in body.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                unwanted.decompose()
            paragraphs = body.find_all('p')
            full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        if len(full_text) < 200:
            return None
        return {'title': title, 'published_at': published_at, 'author': author, 'full_text': full_text[:10000]}
    except Exception as e:
        logger.warning(f"Extraction error: {e}")
        return None


def discover_article_links(soup: BeautifulSoup, base_url: str, max_links: int = 50) -> List[str]:
    links = set()
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href:
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            base_parsed = urlparse(base_url)
            if parsed.netloc.endswith(base_parsed.netloc.replace('www.', '')):
                path = parsed.path.lower()
                skip = ['/tag/', '/category/', '/author/', '/search/', '/page/', '/feed/', '/about', '/contact']
                if not any(s in path for s in skip) and len(path) > 5:
                    if re.search(r'/[\w]+-[\w]+', path) or '/news/' in path or '/article/' in path:
                        links.add(full_url)
    return list(links)[:max_links]


def scrape_article(url: str, seen_hashes: set) -> dict | None:
    url_hash = get_url_hash(url)
    if url_hash in seen_hashes:
        return None
    random_delay(1.0, 3.0)
    soup, response = get_page(url)
    if not soup or not response:
        return None
    if is_paywall_or_blocked(soup, response):
        logger.info(f"Paywall detected: {url}")
        return None
    result = extract_generic(soup, url)
    if not result:
        return None
    
    from dateutil import parser as date_parser
    published_at = result.get('published_at', '')
    try:
        dt = date_parser.parse(published_at) if published_at else datetime.utcnow()
        published_at = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        published_at = datetime.utcnow().isoformat() + 'Z'
    
    content_hash = get_content_hash(result['title'], published_at)
    if content_hash in seen_hashes:
        return None
    seen_hashes.add(url_hash)
    seen_hashes.add(content_hash)
    
    domain = urlparse(url).netloc.replace('www.', '').split('.')[0].title()
    return {
        'id': url_hash[:32], 'title': result['title'], 'published_at': published_at,
        'source_name': domain, 'source_type': 'SCRAPE', 'url': normalize_url(url),
        'full_text': result['full_text'], 'author': result.get('author', ''),
        'section': '', 'language': 'en', 'retrieved_at': datetime.utcnow().isoformat() + 'Z',
        'url_hash': url_hash, 'content_hash': content_hash
    }


def collect_from_scraping(max_articles: int = 150, seen_hashes: set = None) -> Generator[dict, None, None]:
    if seen_hashes is None:
        seen_hashes = set()
    config = load_config()
    seeds = config.get('SCRAPE_SEEDS', [])
    collected = 0
    
    for seed_config in seeds:
        if collected >= max_articles:
            break
        seed_url = seed_config.get('url') if isinstance(seed_config, dict) else seed_config
        seed_name = seed_config.get('name', seed_url) if isinstance(seed_config, dict) else seed_url
        max_depth = seed_config.get('max_depth', 1) if isinstance(seed_config, dict) else 1
        
        logger.info(f"Processing seed: {seed_name}")
        random_delay(1.0, 2.0)
        soup, response = get_page(seed_url)
        if not soup:
            continue
        
        if max_depth == 0:
            article = scrape_article(seed_url, seen_hashes)
            if article:
                yield article
                collected += 1
            continue
        
        article_urls = discover_article_links(soup, seed_url, max_links=40)
        logger.info(f"Found {len(article_urls)} links from {seed_name}")
        
        for article_url in article_urls:
            if collected >= max_articles:
                break
            article = scrape_article(article_url, seen_hashes)
            if article:
                yield article
                collected += 1
                logger.info(f"Scraped ({collected}/{max_articles}): {article['title'][:50]}...")
    
    logger.info(f"Scraping complete. Total: {collected}")


if __name__ == "__main__":
    articles = list(collect_from_scraping(max_articles=10))
    print(f"Scraped {len(articles)} articles")
