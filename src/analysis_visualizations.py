"""
Comprehensive Analysis & Visualization Script
8 Detailed Analyses with Professional Visualizations for Civil Engineering + AI Data
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from wordcloud import WordCloud

# Configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['axes.labelsize'] = 14

# Color palettes
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'accent': '#F18F01',
    'success': '#C73E1D',
    'gradient': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3A5A40', '#6B4226', '#8B5CF6', '#06B6D4']
}

OUTPUT_DIR = Path(__file__).parent.parent / 'outputs' / 'visualizations'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load data from SQLite database"""
    db_path = Path(__file__).parent.parent / 'data' / 'processed' / 'articles.db'
    conn = sqlite3.connect(db_path)
    
    # Load accepted articles
    df = pd.read_sql_query("SELECT * FROM articles", conn)
    df_rejected = pd.read_sql_query("SELECT * FROM rejected", conn)
    
    conn.close()
    
    # Parse dates
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
    df['year'] = df['published_at'].dt.year
    df['month'] = df['published_at'].dt.to_period('M')
    df['year_month'] = df['published_at'].dt.strftime('%Y-%m')
    
    # Parse keywords JSON
    df['keywords_list'] = df['keywords'].apply(lambda x: json.loads(x) if pd.notna(x) and x else [])
    
    return df, df_rejected


# =============================================================================
# ANALYSIS 1: Category Distribution
# =============================================================================
def analysis_1_category_distribution(df):
    """Analyze and visualize category distribution"""
    print("📊 Analysis 1: Category Distribution")
    
    # Clean and normalize categories
    category_counts = df['category'].value_counts().head(12)
    
    # Create figure with 2 subplots
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # 1. Horizontal Bar Chart
    ax1 = axes[0]
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(category_counts)))[::-1]
    bars = ax1.barh(category_counts.index, category_counts.values, color=colors, edgecolor='white', linewidth=0.5)
    ax1.set_xlabel('Number of Articles')
    ax1.set_title('AI in Civil Engineering: Category Distribution', fontweight='bold', pad=15)
    ax1.invert_yaxis()
    
    # Add value labels
    for bar, val in zip(bars, category_counts.values):
        ax1.text(val + 1, bar.get_y() + bar.get_height()/2, f'{val}', 
                va='center', fontsize=11, fontweight='bold')
    
    # 2. Pie Chart
    ax2 = axes[1]
    top_categories = category_counts.head(8)
    other_count = category_counts[8:].sum() if len(category_counts) > 8 else 0
    
    if other_count > 0:
        pie_data = pd.concat([top_categories, pd.Series({'Other': other_count})])
    else:
        pie_data = top_categories
    
    colors_pie = plt.cm.Set3(np.linspace(0, 1, len(pie_data)))
    wedges, texts, autotexts = ax2.pie(pie_data.values, labels=pie_data.index, autopct='%1.1f%%',
                                        colors=colors_pie, startangle=90, pctdistance=0.75)
    ax2.set_title('Category Share Distribution', fontweight='bold', pad=15)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '1_category_distribution.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 1_category_distribution.png")


# =============================================================================
# ANALYSIS 2: Time-based Trend Analysis
# =============================================================================
def analysis_2_time_trends(df):
    """Analyze and visualize time-based trends"""
    print("📊 Analysis 2: Time-based Trends")
    
    # Filter valid dates
    df_dated = df[df['published_at'].notna()].copy()
    
    if len(df_dated) < 10:
        print("  ⚠ Not enough dated articles for trend analysis")
        return
    
    # Monthly trend
    monthly_counts = df_dated.groupby('year_month').size().reset_index(name='count')
    monthly_counts = monthly_counts.sort_values('year_month')
    
    # Get top 5 categories for trend
    top_categories = df_dated['category'].value_counts().head(5).index.tolist()
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # 1. Overall trend line
    ax1 = axes[0]
    ax1.fill_between(range(len(monthly_counts)), monthly_counts['count'], alpha=0.3, color=COLORS['primary'])
    ax1.plot(range(len(monthly_counts)), monthly_counts['count'], 
             color=COLORS['primary'], linewidth=2.5, marker='o', markersize=6)
    ax1.set_xticks(range(0, len(monthly_counts), max(1, len(monthly_counts)//10)))
    ax1.set_xticklabels(monthly_counts['year_month'].iloc[::max(1, len(monthly_counts)//10)], rotation=45, ha='right')
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Number of Articles')
    ax1.set_title('AI in Civil Engineering: Publication Trend Over Time', fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3)
    
    # 2. Category trends
    ax2 = axes[1]
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_categories)))
    
    for idx, cat in enumerate(top_categories):
        cat_monthly = df_dated[df_dated['category'] == cat].groupby('year_month').size()
        cat_monthly = cat_monthly.reindex(monthly_counts['year_month'], fill_value=0)
        ax2.plot(range(len(cat_monthly)), cat_monthly.values, 
                label=cat, linewidth=2, marker='o', markersize=4, color=colors[idx])
    
    ax2.set_xticks(range(0, len(monthly_counts), max(1, len(monthly_counts)//10)))
    ax2.set_xticklabels(monthly_counts['year_month'].iloc[::max(1, len(monthly_counts)//10)], rotation=45, ha='right')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Number of Articles')
    ax2.set_title('Category Trends Over Time', fontweight='bold', pad=15)
    ax2.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '2_time_trends.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 2_time_trends.png")


# =============================================================================
# ANALYSIS 3: Application Stage Distribution
# =============================================================================
def analysis_3_application_stage(df):
    """Analyze and visualize application stage distribution"""
    print("📊 Analysis 3: Application Stage Distribution")
    
    stage_counts = df['application_stage'].value_counts()
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Donut Chart
    ax1 = axes[0]
    colors = plt.cm.Pastel1(np.linspace(0, 1, len(stage_counts)))
    wedges, texts, autotexts = ax1.pie(stage_counts.values, labels=stage_counts.index, 
                                        autopct='%1.1f%%', colors=colors,
                                        wedgeprops=dict(width=0.6), startangle=90)
    ax1.set_title('AI Application Stage in Construction Projects', fontweight='bold', pad=15)
    
    # Add center text
    ax1.text(0, 0, f'Total\n{len(df)}', ha='center', va='center', fontsize=16, fontweight='bold')
    
    # 2. Sunburst-like stacked bar
    ax2 = axes[1]
    
    # Cross-tabulation with category
    stage_cat = pd.crosstab(df['application_stage'], df['category'])
    top_cats = df['category'].value_counts().head(6).index
    stage_cat = stage_cat[top_cats]
    
    stage_cat.plot(kind='barh', stacked=True, ax=ax2, colormap='Set2', edgecolor='white', linewidth=0.5)
    ax2.set_xlabel('Number of Articles')
    ax2.set_title('Application Stage × Category Breakdown', fontweight='bold', pad=15)
    ax2.legend(title='Category', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '3_application_stage.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 3_application_stage.png")


# =============================================================================
# ANALYSIS 4: Keyword Analysis
# =============================================================================
def analysis_4_keywords(df):
    """Analyze and visualize keyword distribution"""
    print("📊 Analysis 4: Keyword Analysis")
    
    # Extract all keywords
    all_keywords = []
    for kw_list in df['keywords_list']:
        if isinstance(kw_list, list):
            all_keywords.extend([kw.lower().strip() for kw in kw_list if kw])
    
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(20)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # 1. Bar Chart
    ax1 = axes[0]
    keywords, counts = zip(*top_keywords) if top_keywords else ([], [])
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(keywords)))
    bars = ax1.barh(list(keywords)[::-1], list(counts)[::-1], color=colors[::-1], edgecolor='white')
    ax1.set_xlabel('Frequency')
    ax1.set_title('Top 20 Keywords in AI + Civil Engineering', fontweight='bold', pad=15)
    
    # Add value labels
    for bar, val in zip(bars, list(counts)[::-1]):
        ax1.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val}', 
                va='center', fontsize=10)
    
    # 2. Word Cloud
    ax2 = axes[1]
    if keyword_counts:
        wordcloud = WordCloud(width=800, height=400, background_color='white',
                             colormap='viridis', max_words=100, max_font_size=100,
                             prefer_horizontal=0.7).generate_from_frequencies(keyword_counts)
        ax2.imshow(wordcloud, interpolation='bilinear')
        ax2.axis('off')
        ax2.set_title('Keyword Word Cloud', fontweight='bold', pad=15)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '4_keywords.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 4_keywords.png")


# =============================================================================
# ANALYSIS 5: Source Analysis
# =============================================================================
def analysis_5_sources(df):
    """Analyze and visualize source distribution"""
    print("📊 Analysis 5: Source Analysis")
    
    source_counts = df['source_name'].value_counts().head(15)
    source_type_counts = df['source_type'].value_counts()
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # 1. Top Sources Bar Chart
    ax1 = axes[0]
    colors = plt.cm.RdYlBu(np.linspace(0.2, 0.8, len(source_counts)))
    ax1.barh(source_counts.index[::-1], source_counts.values[::-1], color=colors, edgecolor='white')
    ax1.set_xlabel('Number of Articles')
    ax1.set_title('Top 15 News/Data Sources', fontweight='bold', pad=15)
    
    # Add value labels
    for i, (idx, val) in enumerate(zip(source_counts.index[::-1], source_counts.values[::-1])):
        ax1.text(val + 0.5, i, f'{val}', va='center', fontsize=10)
    
    # 2. Source Type Breakdown
    ax2 = axes[1]
    colors_type = [COLORS['primary'], COLORS['secondary'], COLORS['accent']][:len(source_type_counts)]
    wedges, texts, autotexts = ax2.pie(source_type_counts.values, labels=source_type_counts.index,
                                        autopct='%1.1f%%', colors=colors_type, startangle=90,
                                        explode=[0.05]*len(source_type_counts))
    ax2.set_title('Distribution by Source Type', fontweight='bold', pad=15)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '5_sources.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 5_sources.png")


# =============================================================================
# ANALYSIS 6: Time-Topic Relationship (Heatmap)
# =============================================================================
def analysis_6_time_topic(df):
    """Analyze and visualize time-topic relationship"""
    print("📊 Analysis 6: Time-Topic Relationship")
    
    df_dated = df[df['published_at'].notna()].copy()
    
    if len(df_dated) < 10:
        print("  ⚠ Not enough dated articles")
        return
    
    # Create year-month period
    df_dated['period'] = df_dated['published_at'].dt.to_period('M').astype(str)
    
    # Get top categories
    top_cats = df_dated['category'].value_counts().head(8).index.tolist()
    df_filtered = df_dated[df_dated['category'].isin(top_cats)]
    
    # Create pivot table
    pivot = pd.crosstab(df_filtered['category'], df_filtered['period'])
    
    # Sort columns by date
    pivot = pivot.reindex(columns=sorted(pivot.columns))
    
    # Limit columns for visibility
    if len(pivot.columns) > 12:
        pivot = pivot.iloc[:, -12:]  # Last 12 months
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Heatmap
    sns.heatmap(pivot, annot=True, fmt='d', cmap='YlOrRd', 
                linewidths=0.5, linecolor='white', ax=ax,
                cbar_kws={'label': 'Number of Articles'})
    
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Category', fontsize=12)
    ax.set_title('Topic Evolution Over Time: Heatmap', fontweight='bold', fontsize=16, pad=15)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '6_time_topic_heatmap.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 6_time_topic_heatmap.png")


# =============================================================================
# ANALYSIS 7: Civil Engineering Area Distribution
# =============================================================================
def analysis_7_civil_eng_areas(df):
    """Analyze and visualize civil engineering area distribution"""
    print("📊 Analysis 7: Civil Engineering Areas")
    
    area_counts = df['civil_engineering_area'].value_counts().head(10)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # 1. Horizontal Bar Chart
    ax1 = axes[0]
    colors = plt.cm.Greens(np.linspace(0.3, 0.9, len(area_counts)))[::-1]
    bars = ax1.barh(area_counts.index[::-1], area_counts.values[::-1], color=colors, edgecolor='white')
    ax1.set_xlabel('Number of Articles')
    ax1.set_title('AI Applications by Civil Engineering Field', fontweight='bold', pad=15)
    
    for bar, val in zip(bars, area_counts.values[::-1]):
        ax1.text(val + 1, bar.get_y() + bar.get_height()/2, f'{val}', 
                va='center', fontsize=11, fontweight='bold')
    
    # 2. Treemap-style visualization using nested pie
    ax2 = axes[1]
    
    # Cross-tab with AI technique
    area_technique = pd.crosstab(df['civil_engineering_area'], df['ai_technique'])
    top_areas = area_counts.head(5).index
    top_techniques = df['ai_technique'].value_counts().head(5).index
    
    area_technique_filtered = area_technique.loc[area_technique.index.isin(top_areas), top_techniques]
    
    area_technique_filtered.plot(kind='bar', stacked=True, ax=ax2, colormap='Spectral', 
                                  edgecolor='white', linewidth=0.5)
    ax2.set_xlabel('Civil Engineering Area')
    ax2.set_ylabel('Number of Articles')
    ax2.set_title('CE Area × AI Technique Matrix', fontweight='bold', pad=15)
    ax2.legend(title='AI Technique', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '7_civil_eng_areas.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 7_civil_eng_areas.png")


# =============================================================================
# ANALYSIS 8: AI Technique Distribution
# =============================================================================
def analysis_8_ai_techniques(df):
    """Analyze and visualize AI technique distribution"""
    print("📊 Analysis 8: AI Techniques")
    
    technique_counts = df['ai_technique'].value_counts().head(10)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # 1. Polar/Radar-like Bar Chart
    ax1 = axes[0]
    colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(technique_counts)))
    
    bars = ax1.bar(range(len(technique_counts)), technique_counts.values, 
                   color=colors, edgecolor='white', linewidth=1, width=0.7)
    ax1.set_xticks(range(len(technique_counts)))
    ax1.set_xticklabels(technique_counts.index, rotation=45, ha='right', fontsize=10)
    ax1.set_ylabel('Number of Articles')
    ax1.set_title('AI Techniques Used in Civil Engineering', fontweight='bold', pad=15)
    
    # Add value labels on bars
    for bar, val in zip(bars, technique_counts.values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val}', 
                ha='center', fontsize=10, fontweight='bold')
    
    # 2. Bubble Chart: AI Technique vs Category
    ax2 = axes[1]
    
    tech_cat = pd.crosstab(df['ai_technique'], df['category'])
    top_techs = technique_counts.head(5).index
    top_cats = df['category'].value_counts().head(5).index
    
    tech_cat_filtered = tech_cat.loc[tech_cat.index.isin(top_techs), top_cats]
    
    # Create bubble positions
    x_pos = []
    y_pos = []
    sizes = []
    colors_bubble = []
    
    for i, tech in enumerate(tech_cat_filtered.index):
        for j, cat in enumerate(tech_cat_filtered.columns):
            x_pos.append(j)
            y_pos.append(i)
            sizes.append(tech_cat_filtered.loc[tech, cat] * 20 + 10)
            colors_bubble.append(tech_cat_filtered.loc[tech, cat])
    
    scatter = ax2.scatter(x_pos, y_pos, s=sizes, c=colors_bubble, cmap='YlOrRd', 
                          alpha=0.7, edgecolors='black', linewidths=0.5)
    
    ax2.set_xticks(range(len(tech_cat_filtered.columns)))
    ax2.set_xticklabels(tech_cat_filtered.columns, rotation=45, ha='right', fontsize=10)
    ax2.set_yticks(range(len(tech_cat_filtered.index)))
    ax2.set_yticklabels(tech_cat_filtered.index, fontsize=10)
    ax2.set_title('AI Technique × Category Bubble Matrix', fontweight='bold', pad=15)
    
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('Article Count')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '8_ai_techniques.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 8_ai_techniques.png")


# =============================================================================
# SUMMARY DASHBOARD
# =============================================================================
def create_summary_dashboard(df, df_rejected):
    """Create a summary dashboard with key metrics"""
    print("📊 Creating Summary Dashboard")
    
    fig = plt.figure(figsize=(18, 12))
    
    # Create grid
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
    
    # Title
    fig.suptitle('AI in Civil Engineering: Research & News Analysis Dashboard', 
                 fontsize=20, fontweight='bold', y=0.98)
    
    # 1. Key Metrics (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')
    
    total = len(df) + len(df_rejected)
    metrics_text = f"""
    📈 KEY METRICS
    ─────────────────
    Total Analyzed: {total}
    AI Relevant: {len(df)} ({len(df)/total*100:.1f}%)
    Not Relevant: {len(df_rejected)} ({len(df_rejected)/total*100:.1f}%)
    
    📅 Date Range:
    {df['published_at'].min().strftime('%Y-%m') if pd.notna(df['published_at'].min()) else 'N/A'} to 
    {df['published_at'].max().strftime('%Y-%m') if pd.notna(df['published_at'].max()) else 'N/A'}
    """
    ax1.text(0.1, 0.9, metrics_text, transform=ax1.transAxes, fontsize=12,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    # 2. Category Pie
    ax2 = fig.add_subplot(gs[0, 1])
    top_cats = df['category'].value_counts().head(6)
    ax2.pie(top_cats.values, labels=top_cats.index, autopct='%1.1f%%', 
           colors=plt.cm.Set3(np.linspace(0, 1, len(top_cats))))
    ax2.set_title('Top Categories')
    
    # 3. AI Techniques Pie
    ax3 = fig.add_subplot(gs[0, 2])
    top_techs = df['ai_technique'].value_counts().head(6)
    ax3.pie(top_techs.values, labels=top_techs.index, autopct='%1.1f%%',
           colors=plt.cm.Pastel1(np.linspace(0, 1, len(top_techs))))
    ax3.set_title('Top AI Techniques')
    
    # 4. Category Bar
    ax4 = fig.add_subplot(gs[1, :2])
    cats = df['category'].value_counts().head(10)
    ax4.barh(cats.index[::-1], cats.values[::-1], color=plt.cm.Blues(np.linspace(0.3, 0.9, len(cats)))[::-1])
    ax4.set_xlabel('Articles')
    ax4.set_title('Category Distribution')
    
    # 5. CE Area Bar
    ax5 = fig.add_subplot(gs[1, 2])
    areas = df['civil_engineering_area'].value_counts().head(6)
    ax5.barh(areas.index[::-1], areas.values[::-1], color=plt.cm.Greens(np.linspace(0.3, 0.9, len(areas)))[::-1])
    ax5.set_xlabel('Articles')
    ax5.set_title('CE Areas')
    
    # 6. Timeline
    ax6 = fig.add_subplot(gs[2, :])
    df_dated = df[df['published_at'].notna()]
    if len(df_dated) > 0:
        monthly = df_dated.groupby('year_month').size()
        monthly = monthly.sort_index()
        ax6.fill_between(range(len(monthly)), monthly.values, alpha=0.4, color=COLORS['primary'])
        ax6.plot(range(len(monthly)), monthly.values, color=COLORS['primary'], linewidth=2)
        ax6.set_xticks(range(0, len(monthly), max(1, len(monthly)//8)))
        ax6.set_xticklabels(monthly.index[::max(1, len(monthly)//8)], rotation=45, ha='right')
        ax6.set_ylabel('Articles')
        ax6.set_title('Publication Timeline')
        ax6.grid(True, alpha=0.3)
    
    plt.savefig(OUTPUT_DIR / '0_summary_dashboard.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ Saved: 0_summary_dashboard.png")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("="*60)
    print("AI IN CIVIL ENGINEERING: COMPREHENSIVE ANALYSIS")
    print("="*60)
    print()
    
    # Load data
    print("Loading data...")
    df, df_rejected = load_data()
    print(f"  Loaded {len(df)} accepted + {len(df_rejected)} rejected articles")
    print()
    
    # Run all analyses
    analysis_1_category_distribution(df)
    analysis_2_time_trends(df)
    analysis_3_application_stage(df)
    analysis_4_keywords(df)
    analysis_5_sources(df)
    analysis_6_time_topic(df)
    analysis_7_civil_eng_areas(df)
    analysis_8_ai_techniques(df)
    create_summary_dashboard(df, df_rejected)
    
    print()
    print("="*60)
    print(f"✅ ALL VISUALIZATIONS SAVED TO: {OUTPUT_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
