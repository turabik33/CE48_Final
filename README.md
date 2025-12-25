# CE49X Final Project: AI Applications in Civil Engineering

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Project Overview

This project investigates the intersection of **Artificial Intelligence (AI)** and **Civil Engineering** through Natural Language Processing (NLP) and trend analysis. We collected, processed, and analyzed a corpus of **899 articles** from news sources, APIs, and academic databases to determine which sub-disciplines of Civil Engineering are most actively adopting AI technologies.

### 🎯 Research Question
> **"Which Civil Engineering area is using AI the most?"**

### 📊 Key Findings
- **Construction Management** leads with 276 articles (62.4% of AI-relevant content)
- **Machine Learning** is the dominant AI technique (137 articles)
- **442 articles** (49.2%) identified as directly relevant to AI in Civil Engineering
- AI applications span the entire construction lifecycle: Planning → Design → Construction → Operation → Maintenance

---

## 🏗️ Project Structure

```
CE49X-Final/
├── 📁 config/
│   └── sources.yaml          # Data source configurations
├── 📁 data/
│   ├── raw/                   # Raw collected data (CSV, JSON, JSONL)
│   └── processed/             # Processed data (SQLite DB, classified CSV)
├── 📁 outputs/
│   ├── CE49X_Final_Report.pdf # Final comprehensive report
│   └── visualizations/        # Generated charts and graphs
├── 📁 src/
│   ├── rss_collector.py       # RSS feed data collection
│   ├── api_collector.py       # News API integration (GNews, NewsAPI, Guardian)
│   ├── scholar_collector.py   # Google Scholar via SerpAPI
│   ├── scrape_collector.py    # Web scraping module
│   ├── build_raw_dataset.py   # Dataset aggregation script
│   ├── llm_processor.py       # LLM-based classification (Gemini 2.0 Flash)
│   ├── batch_processor.py     # Batch processing for large datasets
│   ├── analysis_visualizations.py  # 8 comprehensive analyses
│   ├── network_graph.py       # AI-CE relationship network graph
│   └── generate_report.py     # PDF report generator
├── 📁 logs/                   # Execution logs
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
```bash
# Clone the repository
git clone https://github.com/turabik33/CE48_Final.git
cd CE48_Final

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Usage

### 1. Data Collection (Task 1)
```bash
# Collect from RSS feeds
python src/rss_collector.py

# Collect from APIs
python src/api_collector.py

# Collect from Google Scholar
python src/scholar_collector.py --api-key YOUR_SERP_API_KEY

# Build unified dataset
python src/build_raw_dataset.py
```

### 2. LLM Classification (Task 3)
```bash
# Process articles with Gemini 2.0 Flash
python src/batch_processor.py --start 0 --end 200
python src/batch_processor.py --start 200 --end 400
# ... continue in batches
```

### 3. Generate Visualizations (Task 4)
```bash
# Create all 8 analysis charts
python src/analysis_visualizations.py

# Create network graph
python src/network_graph.py
```

### 4. Generate Final Report
```bash
python src/generate_report.py
```

---

## 📈 Visualizations

| Analysis | Description |
|----------|-------------|
| Category Distribution | Bar + Pie charts of AI application categories |
| Time Trends | Publication volume over time |
| Application Stage | Project lifecycle phase analysis |
| Keyword Analysis | Word cloud + top 20 keywords |
| Source Analysis | RSS vs API vs Scraping breakdown |
| Time-Topic Heatmap | Topic evolution over months |
| CE Areas | Civil Engineering discipline distribution |
| AI Techniques | Machine Learning, Robotics, Computer Vision, etc. |
| Network Graph | Co-occurrence relationships between terms |

---

## 📚 Data Sources

### News & Industry
- Google News RSS Feeds
- GNews API
- NewsAPI
- The Guardian Open Platform
- Construction Dive, BIMplus, ENR (Web Scraping)

### Academic
- Google Scholar via SerpAPI

---

## 🧠 Technologies Used

| Category | Tools |
|----------|-------|
| **Data Collection** | requests, feedparser, BeautifulSoup, Selenium |
| **NLP & Classification** | Google Gemini 2.0 Flash LLM |
| **Data Processing** | pandas, numpy, SQLite |
| **Visualization** | matplotlib, seaborn, networkx, wordcloud |
| **Report Generation** | ReportLab |

---

## 👥 Team

- **Umut Gün Turabik**
- **Ali Yigit Akinci**

**Instructor:** Eyüphan Koç

**Course:** CE49X – Introduction to Data Science for Civil Engineering

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Repository

**GitHub:** [https://github.com/turabik33/CE48_Final](https://github.com/turabik33/CE48_Final)
