"""
Build Raw Dataset - Main Orchestrator
Combines RSS, API, and Scraping collectors to build the complete dataset
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import yaml

from rss_collector import collect_from_rss
from api_collector import collect_from_apis
from scrape_collector import collect_from_scraping

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Ensure directories exist
(PROJECT_ROOT / 'logs').mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / 'data' / 'raw').mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'collection.log')
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from sources.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def ensure_directories():
    """Create necessary directories"""
    dirs = ['data/raw', 'logs']
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def save_to_csv(articles: List[dict], filepath: str):
    """Save articles to CSV file"""
    if not articles:
        logger.warning("No articles to save to CSV")
        return
    
    # Define column order
    columns = [
        'id', 'title', 'published_at', 'source_name', 'source_type',
        'url', 'full_text', 'author', 'section', 'language', 'retrieved_at'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for article in articles:
            writer.writerow(article)
    
    logger.info(f"Saved {len(articles)} articles to {filepath}")


def save_to_jsonl(articles: List[dict], filepath: str):
    """Save articles to JSONL file"""
    if not articles:
        logger.warning("No articles to save to JSONL")
        return
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for article in articles:
            # Remove internal fields before saving
            clean_article = {k: v for k, v in article.items() 
                          if k not in ['url_hash', 'content_hash', 'feed_url', 'api_source']}
            f.write(json.dumps(clean_article, ensure_ascii=False) + '\n')
    
    logger.info(f"Saved {len(articles)} articles to {filepath}")


def print_stats(articles: List[dict]):
    """Print collection statistics"""
    if not articles:
        print("\nNo articles collected.")
        return
    
    # Count by source type
    by_type = {}
    for article in articles:
        source_type = article.get('source_type', 'Unknown')
        by_type[source_type] = by_type.get(source_type, 0) + 1
    
    # Count by source name
    by_source = {}
    for article in articles:
        source_name = article.get('source_name', 'Unknown')
        by_source[source_name] = by_source.get(source_name, 0) + 1
    
    print("\n" + "="*60)
    print("COLLECTION STATISTICS")
    print("="*60)
    print(f"\nTotal Articles: {len(articles)}")
    
    print("\nBy Source Type:")
    for stype, count in sorted(by_type.items()):
        print(f"  {stype}: {count} ({count/len(articles)*100:.1f}%)")
    
    print("\nTop 10 Sources:")
    sorted_sources = sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:10]
    for source, count in sorted_sources:
        print(f"  {source}: {count}")
    
    print("="*60 + "\n")


def build_raw_dataset(target_total: int = 700):
    """
    Main function to build the raw dataset
    
    Args:
        target_total: Target number of articles to collect
    """
    logger.info(f"Starting data collection. Target: {target_total} articles")
    
    # Load config
    config = load_config()
    quotas = config.get('QUOTAS', {})
    
    rss_quota = quotas.get('RSS', 300)
    api_quota = quotas.get('API', 250)
    scrape_quota = quotas.get('SCRAPE', 150)
    
    logger.info(f"Quotas - RSS: {rss_quota}, API: {api_quota}, Scrape: {scrape_quota}")
    
    # Ensure directories exist
    ensure_directories()
    
    all_articles = []
    seen_hashes = set()
    
    # Phase 1: RSS Collection
    logger.info("\n" + "="*50)
    logger.info("PHASE 1: RSS COLLECTION")
    logger.info("="*50)
    
    try:
        for article in collect_from_rss(max_articles=rss_quota, seen_hashes=seen_hashes):
            all_articles.append(article)
            if len(all_articles) >= target_total:
                break
    except Exception as e:
        logger.error(f"RSS collection error: {e}")
    
    rss_count = len([a for a in all_articles if a['source_type'] == 'RSS'])
    logger.info(f"RSS phase complete. Collected: {rss_count}")
    
    # Check if we've reached target
    if len(all_articles) >= target_total:
        logger.info("Target reached after RSS phase")
    else:
        # Phase 2: API Collection
        logger.info("\n" + "="*50)
        logger.info("PHASE 2: API COLLECTION")
        logger.info("="*50)
        
        remaining = target_total - len(all_articles)
        api_target = min(api_quota, remaining)
        
        try:
            for article in collect_from_apis(max_articles=api_target, seen_hashes=seen_hashes):
                all_articles.append(article)
                if len(all_articles) >= target_total:
                    break
        except Exception as e:
            logger.error(f"API collection error: {e}")
        
        api_count = len([a for a in all_articles if a['source_type'] == 'API'])
        logger.info(f"API phase complete. Collected: {api_count}")
    
    # Check if we need scraping
    if len(all_articles) >= target_total:
        logger.info("Target reached after API phase")
    else:
        # Phase 3: Web Scraping
        logger.info("\n" + "="*50)
        logger.info("PHASE 3: WEB SCRAPING")
        logger.info("="*50)
        
        remaining = target_total - len(all_articles)
        scrape_target = min(scrape_quota, remaining)
        
        try:
            for article in collect_from_scraping(max_articles=scrape_target, seen_hashes=seen_hashes):
                all_articles.append(article)
                if len(all_articles) >= target_total:
                    break
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        scrape_count = len([a for a in all_articles if a['source_type'] == 'SCRAPE'])
        logger.info(f"Scraping phase complete. Collected: {scrape_count}")
    
    # Print statistics
    print_stats(all_articles)
    
    # Save outputs
    if all_articles:
        csv_path = 'data/raw/articles.csv'
        jsonl_path = 'data/raw/articles.jsonl'
        
        save_to_csv(all_articles, csv_path)
        save_to_jsonl(all_articles, jsonl_path)
        
        logger.info(f"\nCollection complete!")
        logger.info(f"Total articles: {len(all_articles)}")
        logger.info(f"CSV output: {csv_path}")
        logger.info(f"JSONL output: {jsonl_path}")
    else:
        logger.warning("No articles collected!")
    
    return all_articles


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Build raw dataset for Civil Engineering + AI news')
    parser.add_argument('--target', type=int, default=700, help='Target number of articles')
    parser.add_argument('--rss-only', action='store_true', help='Only collect from RSS feeds')
    parser.add_argument('--api-only', action='store_true', help='Only collect from APIs')
    parser.add_argument('--scrape-only', action='store_true', help='Only collect from scraping')
    
    args = parser.parse_args()
    
    if args.rss_only:
        ensure_directories()
        articles = list(collect_from_rss(max_articles=args.target))
        print_stats(articles)
        save_to_csv(articles, 'data/raw/articles.csv')
        save_to_jsonl(articles, 'data/raw/articles.jsonl')
    elif args.api_only:
        ensure_directories()
        articles = list(collect_from_apis(max_articles=args.target))
        print_stats(articles)
        save_to_csv(articles, 'data/raw/articles.csv')
        save_to_jsonl(articles, 'data/raw/articles.jsonl')
    elif args.scrape_only:
        ensure_directories()
        articles = list(collect_from_scraping(max_articles=args.target))
        print_stats(articles)
        save_to_csv(articles, 'data/raw/articles.csv')
        save_to_jsonl(articles, 'data/raw/articles.jsonl')
    else:
        build_raw_dataset(target_total=args.target)
