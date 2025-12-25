"""
Google Scholar Collector Module
Collects academic papers from Google Scholar using SerpAPI
"""

import csv
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Generator, List

from serpapi import GoogleSearch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Search queries for Civil Engineering + AI
SCHOLAR_QUERIES = [
    "civil engineering artificial intelligence",
    "construction machine learning",
    "infrastructure AI deep learning",
    "structural engineering neural network",
    "BIM artificial intelligence",
    "smart construction automation",
    "digital twin construction",
    "construction robotics",
    "predictive maintenance infrastructure",
    "computer vision construction",
    "3D printing construction AI",
    "green building machine learning",
    "autonomous construction equipment",
    "IoT construction monitoring",
    "construction safety AI",
]


def get_url_hash(url: str) -> str:
    """Generate hash from URL"""
    return hashlib.sha256(url.encode()).hexdigest()


def search_google_scholar(
    api_key: str,
    query: str,
    num_results: int = 20,
    start: int = 0
) -> List[dict]:
    """
    Search Google Scholar using SerpAPI
    
    Args:
        api_key: SerpAPI key
        query: Search query
        num_results: Number of results to fetch
        start: Starting position for pagination
    
    Returns:
        List of paper dictionaries
    """
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": num_results,
        "start": start,
        "hl": "en"
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            logger.error(f"SerpAPI error: {results['error']}")
            return []
        
        organic_results = results.get("organic_results", [])
        return organic_results
        
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}")
        return []


def parse_paper(result: dict, query: str) -> dict:
    """Parse a single paper result into our schema"""
    
    # Get publication info
    pub_info = result.get("publication_info", {})
    
    # Get link
    link = result.get("link", "")
    if not link:
        # Try resources
        resources = result.get("resources", [])
        if resources:
            link = resources[0].get("link", "")
    
    if not link:
        link = f"https://scholar.google.com/scholar?q={result.get('title', '')}"
    
    url_hash = get_url_hash(link)
    
    # Parse year from summary
    summary = pub_info.get("summary", "")
    year = ""
    import re
    year_match = re.search(r'\b(19|20)\d{2}\b', summary)
    if year_match:
        year = year_match.group(0)
    
    # Get authors
    authors = []
    for author in pub_info.get("authors", []):
        authors.append(author.get("name", ""))
    
    return {
        "id": url_hash[:32],
        "title": result.get("title", ""),
        "published_at": f"{year}-01-01T00:00:00Z" if year else "",
        "source_name": "Google Scholar",
        "source_type": "SCHOLAR",
        "url": link,
        "full_text": result.get("snippet", ""),
        "author": ", ".join(authors),
        "section": query,  # Store the query as section
        "language": "en",
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "url_hash": url_hash,
        "cited_by": result.get("inline_links", {}).get("cited_by", {}).get("total", 0),
        "publication_info": summary
    }


def collect_from_scholar(
    api_key: str,
    max_papers: int = 200,
    seen_hashes: set = None
) -> Generator[dict, None, None]:
    """
    Collect papers from Google Scholar
    
    Args:
        api_key: SerpAPI key
        max_papers: Maximum number of papers to collect
        seen_hashes: Set of already seen URL hashes
    
    Yields:
        Paper dictionaries
    """
    if seen_hashes is None:
        seen_hashes = set()
    
    collected = 0
    
    for query in SCHOLAR_QUERIES:
        if collected >= max_papers:
            break
        
        logger.info(f"Searching Google Scholar: {query}")
        
        # Fetch results (20 per query to stay within free tier)
        results = search_google_scholar(api_key, query, num_results=20)
        
        logger.info(f"Found {len(results)} results for: {query}")
        
        for result in results:
            if collected >= max_papers:
                break
            
            paper = parse_paper(result, query)
            
            # Check for duplicates
            if paper["url_hash"] in seen_hashes:
                continue
            
            seen_hashes.add(paper["url_hash"])
            collected += 1
            
            yield paper
            logger.info(f"Collected ({collected}/{max_papers}): {paper['title'][:50]}...")
    
    logger.info(f"Scholar collection complete. Total: {collected} papers")


def save_papers(papers: List[dict], output_dir: str = "data/raw"):
    """Save papers to CSV and JSONL"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    csv_path = Path(output_dir) / "scholar_papers.csv"
    jsonl_path = Path(output_dir) / "scholar_papers.jsonl"
    
    # CSV columns
    columns = [
        "id", "title", "published_at", "source_name", "source_type",
        "url", "full_text", "author", "section", "language", 
        "retrieved_at", "cited_by", "publication_info"
    ]
    
    # Save CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    
    # Save JSONL
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for paper in papers:
            clean_paper = {k: v for k, v in paper.items() if k != "url_hash"}
            f.write(json.dumps(clean_paper, ensure_ascii=False) + "\n")
    
    logger.info(f"Saved {len(papers)} papers to {csv_path} and {jsonl_path}")
    return csv_path, jsonl_path


def main():
    """Main function to collect Google Scholar papers"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect papers from Google Scholar")
    parser.add_argument("--api-key", type=str, help="SerpAPI key", 
                        default=os.environ.get("SERP_API_KEY"))
    parser.add_argument("--max-papers", type=int, default=200, 
                        help="Maximum papers to collect")
    parser.add_argument("--output-dir", type=str, default="data/raw",
                        help="Output directory")
    
    args = parser.parse_args()
    
    if not args.api_key:
        logger.error("No API key provided. Use --api-key or set SERP_API_KEY env var")
        return
    
    # Collect papers
    papers = list(collect_from_scholar(args.api_key, args.max_papers))
    
    # Print stats
    print(f"\n{'='*60}")
    print("GOOGLE SCHOLAR COLLECTION STATISTICS")
    print(f"{'='*60}")
    print(f"Total Papers: {len(papers)}")
    
    # Count by query
    by_query = {}
    for paper in papers:
        q = paper.get("section", "Unknown")
        by_query[q] = by_query.get(q, 0) + 1
    
    print("\nBy Search Query:")
    for query, count in sorted(by_query.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {query[:40]}: {count}")
    
    # Save
    if papers:
        save_papers(papers, args.output_dir)


if __name__ == "__main__":
    main()
