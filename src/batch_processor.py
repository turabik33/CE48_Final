"""
Batch LLM Processor - Process articles in chunks
Usage: python batch_processor.py --start 0 --end 200
"""

import csv
import json
import sqlite3
import time
import argparse
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

# Configuration
GEMINI_API_KEY = "AIzaSyCrWCxXMnrXGoJF5g2iWYxdhnw8a11xIi0"
MODEL_NAME = "gemini-2.0-flash"
RATE_LIMIT_DELAY = 3.0

# Prompt template
PROMPT = """You are an expert in Civil Engineering and AI. Analyze this article:

TITLE: {title}
CONTENT: {content}

Is this about AI/ML/Deep Learning applied to Civil Engineering/Construction?
(Must contain ACTUAL AI/ML technology, not just digitalization or software)

Respond ONLY in this JSON format:
{{
    "is_relevant": true/false,
    "rejection_reason": "reason if false, empty if true",
    "category": "Safety/BIM/Cost Estimation/Scheduling/Quality Control/Monitoring/Design/Maintenance/Other",
    "civil_engineering_area": "Structural/Geotechnical/Transportation/Construction Management/Hydraulic/Environmental/Materials/Surveying/General",
    "ai_technique": "Computer Vision/Machine Learning/Deep Learning/NLP/Predictive Analytics/Robotics/Other",
    "application_stage": "Planning/Design/Construction/Operation/Maintenance/Multiple",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "summary": "2 sentence summary"
}}
"""

def init_db():
    """Initialize or connect to database"""
    db_path = Path(__file__).parent.parent / 'data' / 'processed' / 'articles.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY, title TEXT, published_at TEXT, source_name TEXT,
        source_type TEXT, url TEXT, author TEXT, data_source TEXT, full_text TEXT,
        category TEXT, civil_engineering_area TEXT, ai_technique TEXT,
        application_stage TEXT, keywords TEXT, summary TEXT, processed_at TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS rejected (
        id TEXT PRIMARY KEY, title TEXT, rejection_reason TEXT, processed_at TEXT
    )''')
    
    conn.commit()
    return conn

def load_articles():
    """Load all articles from CSV"""
    csv_path = Path(__file__).parent.parent / 'data' / 'raw' / 'all_data.csv'
    with open(csv_path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def process_article(model, article):
    """Process single article with retry"""
    prompt = PROMPT.format(
        title=article.get('title', '')[:200],
        content=article.get('full_text', '')[:1500]
    )
    
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('```')[1].replace('json', '').strip()
            
            result = json.loads(text)
            result['id'] = article['id']
            result['processed_at'] = datetime.utcnow().isoformat() + 'Z'
            return result
            
        except json.JSONDecodeError as e:
            return {'id': article['id'], 'is_relevant': False, 
                    'rejection_reason': f'JSON error: {str(e)[:50]}',
                    'processed_at': datetime.utcnow().isoformat() + 'Z'}
        except Exception as e:
            if attempt < 2:
                time.sleep((attempt + 1) * 5)
                continue
            return {'id': article['id'], 'is_relevant': False,
                    'rejection_reason': f'API error: {str(e)[:100]}',
                    'processed_at': datetime.utcnow().isoformat() + 'Z'}
    
    return {'id': article['id'], 'is_relevant': False,
            'rejection_reason': 'Max retries exceeded',
            'processed_at': datetime.utcnow().isoformat() + 'Z'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--end', type=int, default=200, help='End index')
    args = parser.parse_args()
    
    print(f"="*60)
    print(f"BATCH PROCESSING: Articles {args.start} to {args.end}")
    print(f"="*60)
    
    # Initialize
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    conn = init_db()
    cursor = conn.cursor()
    
    # Load articles
    articles = load_articles()[args.start:args.end]
    print(f"Processing {len(articles)} articles...\n")
    
    accepted = 0
    rejected = 0
    start_time = time.time()
    
    for i, article in enumerate(articles):
        result = process_article(model, article)
        
        if result.get('is_relevant'):
            accepted += 1
            merged = {**article, **result}
            keywords_json = json.dumps(result.get('keywords', []))
            cursor.execute('''INSERT OR REPLACE INTO articles 
                (id, title, published_at, source_name, source_type, url, author, 
                 data_source, full_text, category, civil_engineering_area, 
                 ai_technique, application_stage, keywords, summary, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (article['id'], article['title'], article.get('published_at'),
                 article.get('source_name'), article.get('source_type'), article.get('url'),
                 article.get('author'), article.get('data_source'), article.get('full_text'),
                 result.get('category'), result.get('civil_engineering_area'),
                 result.get('ai_technique'), result.get('application_stage'),
                 keywords_json, result.get('summary'), result.get('processed_at')))
            status = "✓"
        else:
            rejected += 1
            cursor.execute('''INSERT OR REPLACE INTO rejected 
                (id, title, rejection_reason, processed_at) VALUES (?, ?, ?, ?)''',
                (article['id'], article['title'], 
                 result.get('rejection_reason', 'Unknown'), result.get('processed_at')))
            status = "✗"
        
        conn.commit()
        
        idx = args.start + i + 1
        print(f"\r[{idx}/{args.end}] {status} Accepted: {accepted}, Rejected: {rejected}", end='', flush=True)
        time.sleep(RATE_LIMIT_DELAY)
    
    elapsed = time.time() - start_time
    print(f"\n\n{'='*60}")
    print(f"BATCH COMPLETE: {args.start}-{args.end}")
    print(f"{'='*60}")
    print(f"Accepted: {accepted} ({accepted/len(articles)*100:.1f}%)")
    print(f"Rejected: {rejected} ({rejected/len(articles)*100:.1f}%)")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(articles):.2f}s per article)")
    print(f"{'='*60}")
    
    conn.close()

if __name__ == "__main__":
    main()
