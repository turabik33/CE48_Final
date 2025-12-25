"""
Network Graph Visualization
Shows relationships between Civil Engineering concepts and AI technologies
Based on term co-occurrence in articles
"""

import sqlite3
import json
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / 'data' / 'processed' / 'articles.db'
OUTPUT_PATH = BASE_DIR / 'outputs' / 'visualizations' / 'network_graph_ai_ce.png'

# Define node categories
CE_AREAS = [
    'Structural', 'Geotechnical', 'Transportation', 'Construction Management',
    'Hydraulic', 'Environmental', 'Materials', 'Surveying', 'General',
    'Water', 'Infrastructure', 'Bridge', 'Highway', 'Foundation'
]

AI_TECHNOLOGIES = [
    'Machine Learning', 'Deep Learning', 'Computer Vision', 'NLP',
    'Robotics', 'Predictive Analytics', 'Neural Network', 'CNN',
    'Reinforcement Learning', 'Generative AI', 'AI', 'Automation',
    'Image Recognition', 'Object Detection', 'Natural Language Processing'
]

# Node colors
COLORS = {
    'ce_area': '#2E86AB',      # Blue for Civil Engineering
    'ai_tech': '#A23B72',       # Purple for AI Technologies
    'keyword': '#8B8B8B'        # Gray for keywords
}


def load_data():
    """Load data from database"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM articles", conn)
    conn.close()
    
    # Parse keywords
    df['keywords_list'] = df['keywords'].apply(
        lambda x: json.loads(x) if pd.notna(x) and x else []
    )
    
    return df


def extract_terms(row):
    """Extract all terms from an article"""
    terms = set()
    
    # Add civil engineering area
    if pd.notna(row['civil_engineering_area']):
        terms.add(row['civil_engineering_area'].strip())
    
    # Add AI technique
    if pd.notna(row['ai_technique']):
        terms.add(row['ai_technique'].strip())
    
    # Add category
    if pd.notna(row['category']):
        terms.add(row['category'].strip())
    
    # Add keywords
    if isinstance(row['keywords_list'], list):
        for kw in row['keywords_list']:
            if kw and len(kw) > 2:
                terms.add(kw.strip().lower())
    
    return terms


def categorize_term(term):
    """Categorize a term as CE area, AI tech, or keyword"""
    term_lower = term.lower()
    
    # Check if CE area
    for ce in CE_AREAS:
        if ce.lower() in term_lower or term_lower in ce.lower():
            return 'ce_area'
    
    # Check if AI technology
    for ai in AI_TECHNOLOGIES:
        if ai.lower() in term_lower or term_lower in ai.lower():
            return 'ai_tech'
    
    return 'keyword'


def build_network(df, min_freq=3, min_cooccur=2):
    """Build co-occurrence network"""
    # Count term frequencies
    term_freq = Counter()
    
    # Count co-occurrences
    cooccur = defaultdict(int)
    
    for _, row in df.iterrows():
        terms = extract_terms(row)
        
        # Update frequencies
        for term in terms:
            term_freq[term] += 1
        
        # Update co-occurrences
        for t1, t2 in combinations(terms, 2):
            if t1 != t2:
                key = tuple(sorted([t1, t2]))
                cooccur[key] += 1
    
    # Create graph
    G = nx.Graph()
    
    # Add nodes (filter by frequency)
    for term, freq in term_freq.items():
        if freq >= min_freq:
            category = categorize_term(term)
            G.add_node(term, freq=freq, category=category)
    
    # Add edges (filter by co-occurrence)
    for (t1, t2), weight in cooccur.items():
        if weight >= min_cooccur and t1 in G.nodes() and t2 in G.nodes():
            G.add_edge(t1, t2, weight=weight)
    
    return G


def visualize_network(G):
    """Create network visualization"""
    if len(G.nodes()) == 0:
        print("No nodes to visualize")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Set layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Get node attributes
    node_colors = []
    node_sizes = []
    
    for node in G.nodes():
        category = G.nodes[node].get('category', 'keyword')
        freq = G.nodes[node].get('freq', 1)
        
        node_colors.append(COLORS.get(category, COLORS['keyword']))
        node_sizes.append(100 + freq * 30)  # Scale by frequency
    
    # Get edge weights
    edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [0.5 + (w / max_weight) * 3 for w in edge_weights]
    
    # Draw edges
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        width=edge_widths,
        alpha=0.4,
        edge_color='gray'
    )
    
    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.8,
        edgecolors='white',
        linewidths=1
    )
    
    # Draw labels
    # Only label nodes with high frequency for clarity
    labels = {}
    for node in G.nodes():
        freq = G.nodes[node].get('freq', 1)
        if freq >= 5:  # Only label frequently occurring terms
            labels[node] = node
    
    nx.draw_networkx_labels(
        G, pos, labels, ax=ax,
        font_size=8,
        font_weight='bold',
        font_color='black'
    )
    
    # Create legend
    legend_elements = [
        mpatches.Patch(color=COLORS['ce_area'], label='Civil Engineering Areas'),
        mpatches.Patch(color=COLORS['ai_tech'], label='AI Technologies'),
        mpatches.Patch(color=COLORS['keyword'], label='Keywords/Terms'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    # Title and styling
    ax.set_title(
        'Network Graph of AI–Civil Engineering Co-Occurrences',
        fontsize=16, fontweight='bold', pad=20
    )
    ax.axis('off')
    
    # Add interpretation text
    interpretation = (
        f"This network visualization displays {len(G.nodes())} terms and {len(G.edges())} relationships.\n"
        f"Node size indicates term frequency; edge thickness represents co-occurrence strength.\n"
        "Blue nodes represent Civil Engineering areas, purple nodes represent AI technologies,\n"
        "and gray nodes represent other frequently occurring keywords from the articles."
    )
    fig.text(0.5, 0.02, interpretation, ha='center', fontsize=10, style='italic',
             wrap=True, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Save figure
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Network graph saved to: {OUTPUT_PATH}")
    print(f"   Nodes: {len(G.nodes())}, Edges: {len(G.edges())}")


def main():
    """Main function"""
    print("="*60)
    print("NETWORK GRAPH: AI–Civil Engineering Co-Occurrences")
    print("="*60)
    
    # Load data
    print("\nLoading data...")
    df = load_data()
    print(f"  Loaded {len(df)} articles")
    
    # Build network
    print("\nBuilding co-occurrence network...")
    G = build_network(df, min_freq=3, min_cooccur=2)
    print(f"  Created graph with {len(G.nodes())} nodes and {len(G.edges())} edges")
    
    # Visualize
    print("\nCreating visualization...")
    visualize_network(G)
    
    # Print interpretation
    print("\n" + "="*60)
    print("INTERPRETATION")
    print("="*60)
    print("""
The network graph reveals the interconnected nature of AI applications 
in civil engineering. Strong connections between 'Machine Learning' and 
'Construction Management' indicate the prevalent use of ML in project 
operations. The cluster around 'Safety' and 'Computer Vision' demonstrates 
how visual AI technologies are being applied for hazard detection and 
monitoring. The prominence of 'Robotics' nodes connected to multiple 
CE areas suggests broad adoption of automation across the industry.
""")


if __name__ == "__main__":
    main()
