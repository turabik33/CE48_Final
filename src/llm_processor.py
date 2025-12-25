"""
LLM Processor Module
Uses Gemini 2.0 Flash to filter and classify Civil Engineering + AI articles
"""

import csv
import json
import sqlite3
import time
import asyncio
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import google.generativeai as genai

# Configuration
GEMINI_API_KEY = "AIzaSyCrWCxXMnrXGoJF5g2iWYxdhnw8a11xIi0"
MODEL_NAME = "gemini-2.0-flash"  # Correct model name
MAX_WORKERS = 10  # Parallel requests
RATE_LIMIT_DELAY = 4.0  # 4 seconds between requests for stability

# Categories
CATEGORIES = [
    "Safety", "BIM/Digital Twin", "Cost Estimation", "Scheduling", 
    "Quality Control", "Monitoring", "Design", "Maintenance",
    "Resource Management", "Risk Assessment", "Other"
]

CIVIL_ENGINEERING_AREAS = [
    "Structural", "Geotechnical", "Transportation", "Construction Management",
    "Hydraulic/Water", "Environmental", "Materials", "Surveying/GIS", "General"
]

AI_TECHNIQUES = [
    "Computer Vision", "Machine Learning", "Deep Learning", "NLP",
    "Reinforcement Learning", "Generative AI", "Predictive Analytics",
    "Robotics/Automation", "Other"
]

APPLICATION_STAGES = [
    "Planning", "Design", "Construction", "Operation", "Maintenance", "Multiple"
]

# Prompt template
CLASSIFICATION_PROMPT = """You are an expert in Civil Engineering and Artificial Intelligence. Analyze the following article and determine:

1. Is this article specifically about AI/ML/Deep Learning applied to Civil Engineering or Construction? 
   - Must contain ACTUAL AI/ML technology (not just digitalization, software, or IoT without AI)
   - Answer: YES or NO

2. If YES, classify the article:

TITLE: {title}

CONTENT: {content}

Respond in this exact JSON format (nothing else):
{{
    "is_relevant": true/false,
    "rejection_reason": "reason if not relevant, empty string if relevant",
    "category": "one of: Safety, BIM/Digital Twin, Cost Estimation, Scheduling, Quality Control, Monitoring, Design, Maintenance, Resource Management, Risk Assessment, Other",
    "civil_engineering_area": "one of: Structural, Geotechnical, Transportation, Construction Management, Hydraulic/Water, Environmental, Materials, Surveying/GIS, General",
    "ai_technique": "one of: Computer Vision, Machine Learning, Deep Learning, NLP, Reinforcement Learning, Generative AI, Predictive Analytics, Robotics/Automation, Other",
    "application_stage": "one of: Planning, Design, Construction, Operation, Maintenance, Multiple",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "summary": "2-3 sentence summary in English"
}}

If not relevant (is_relevant: false), still provide rejection_reason but other fields can be empty strings or empty arrays.
"""


def init_gemini():
    """Initialize Gemini API"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    return model


def process_article(model, article: dict, max_retries: int = 3) -> dict:
    """Process a single article with Gemini with retry mechanism"""
    title = article.get('title', '')
    content = article.get('full_text', '')[:2000]  # Limit content length
    
    prompt = CLASSIFICATION_PROMPT.format(title=title, content=content)
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            result['id'] = article['id']
            result['processed_at'] = datetime.utcnow().isoformat() + 'Z'
            return result
            
        except json.JSONDecodeError as e:
            return {
                'id': article['id'],
                'is_relevant': False,
                'rejection_reason': f'JSON parse error: {str(e)}',
                'processed_at': datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'quota' in error_str.lower() or 'API_KEY_INVALID' in error_str:
                # Rate limit or transient error - retry with backoff
                wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                time.sleep(wait_time)
                continue
            else:
                return {
                    'id': article['id'],
                    'is_relevant': False,
                    'rejection_reason': f'API error: {error_str[:200]}',
                    'processed_at': datetime.utcnow().isoformat() + 'Z'
                }
    
    # All retries failed
    return {
        'id': article['id'],
        'is_relevant': False,
        'rejection_reason': 'Max retries exceeded',
        'processed_at': datetime.utcnow().isoformat() + 'Z'
    }


def process_batch(articles: list, progress_callback=None) -> tuple:
    """Process articles in parallel"""
    model = init_gemini()
    
    accepted = []
    rejected = []
    
    total = len(articles)
    
    for i, article in enumerate(articles):
        result = process_article(model, article)
        
        if result.get('is_relevant', False):
            # Merge original article data with classification
            merged = {**article, **result}
            accepted.append(merged)
        else:
            rejected.append({
                'id': article['id'],
                'title': article['title'],
                'rejection_reason': result.get('rejection_reason', 'Unknown'),
                'processed_at': result.get('processed_at', '')
            })
        
        if progress_callback:
            progress_callback(i + 1, total, result.get('is_relevant', False))
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    return accepted, rejected


def create_database(db_path: str = None):
    """Create SQLite database with tables"""
    if db_path is None:
        db_path = Path(__file__).parent.parent / 'data' / 'processed' / 'articles.db'
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Accepted articles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            published_at TEXT,
            source_name TEXT,
            source_type TEXT,
            url TEXT,
            author TEXT,
            data_source TEXT,
            full_text TEXT,
            category TEXT,
            civil_engineering_area TEXT,
            ai_technique TEXT,
            application_stage TEXT,
            keywords TEXT,
            summary TEXT,
            processed_at TEXT
        )
    ''')
    
    # Rejected articles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rejected (
            id TEXT PRIMARY KEY,
            title TEXT,
            rejection_reason TEXT,
            processed_at TEXT
        )
    ''')
    
    conn.commit()
    return conn


def save_to_database(conn, accepted: list, rejected: list):
    """Save results to database"""
    cursor = conn.cursor()
    
    # Insert accepted
    for article in accepted:
        keywords_json = json.dumps(article.get('keywords', []))
        cursor.execute('''
            INSERT OR REPLACE INTO articles 
            (id, title, published_at, source_name, source_type, url, author, 
             data_source, full_text, category, civil_engineering_area, 
             ai_technique, application_stage, keywords, summary, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['id'], article['title'], article.get('published_at'),
            article.get('source_name'), article.get('source_type'), article.get('url'),
            article.get('author'), article.get('data_source'), article.get('full_text'),
            article.get('category'), article.get('civil_engineering_area'),
            article.get('ai_technique'), article.get('application_stage'),
            keywords_json, article.get('summary'), article.get('processed_at')
        ))
    
    # Insert rejected
    for article in rejected:
        cursor.execute('''
            INSERT OR REPLACE INTO rejected (id, title, rejection_reason, processed_at)
            VALUES (?, ?, ?, ?)
        ''', (article['id'], article['title'], article['rejection_reason'], article['processed_at']))
    
    conn.commit()


def load_articles(csv_path: str = None) -> list:
    """Load articles from CSV"""
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / 'data' / 'raw' / 'all_data.csv'
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def print_progress(current, total, is_relevant):
    """Print progress"""
    status = "✓" if is_relevant else "✗"
    pct = (current / total) * 100
    print(f"\r[{current}/{total}] {pct:.1f}% {status}", end='', flush=True)


def main():
    """Main function"""
    print("="*60)
    print("LLM PROCESSING - Civil Engineering + AI Classification")
    print("="*60)
    print(f"Model: {MODEL_NAME}")
    print()
    
    # Load articles
    print("Loading articles...")
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    print()
    
    # Create database
    print("Creating database...")
    conn = create_database()
    print("Database created: data/processed/articles.db")
    print()
    
    # Process articles
    print("Processing articles with Gemini...")
    print()
    
    start_time = time.time()
    accepted, rejected = process_batch(articles, progress_callback=print_progress)
    end_time = time.time()
    
    print()
    print()
    
    # Save to database
    print("Saving to database...")
    save_to_database(conn, accepted, rejected)
    conn.close()
    
    # Print statistics
    elapsed = end_time - start_time
    print()
    print("="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Total processed: {len(articles)}")
    print(f"Accepted (relevant): {len(accepted)} ({len(accepted)/len(articles)*100:.1f}%)")
    print(f"Rejected: {len(rejected)} ({len(rejected)/len(articles)*100:.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/len(articles):.2f}s per article)")
    print()
    print("Database saved to: data/processed/articles.db")
    print("="*60)
    
    # Also save as CSV for convenience
    if accepted:
        csv_path = 'data/processed/classified_articles.csv'
        columns = ['id', 'title', 'published_at', 'source_name', 'source_type', 
                   'category', 'civil_engineering_area', 'ai_technique', 
                   'application_stage', 'keywords', 'summary']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for article in accepted:
                article['keywords'] = json.dumps(article.get('keywords', []))
                writer.writerow(article)
        
        print(f"Also saved to: {csv_path}")


if __name__ == "__main__":
    main()
