"""
Final Report PDF Generator
Creates a comprehensive PDF report for AI in Civil Engineering research
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, 
                                 PageBreak, Table, TableStyle, ListFlowable, 
                                 ListItem, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from collections import Counter

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / 'outputs'
VIZ_DIR = OUTPUT_DIR / 'visualizations'
PDF_PATH = OUTPUT_DIR / 'Final_Report.pdf'

# Colors
PRIMARY_COLOR = HexColor('#1a365d')
ACCENT_COLOR = HexColor('#2b6cb0')
LIGHT_BG = HexColor('#f7fafc')

def create_styles():
    """Create custom paragraph styles"""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName='Times-Bold',
        fontSize=28,
        leading=34,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=PRIMARY_COLOR
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName='Times-Roman',
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=ACCENT_COLOR
    ))
    
    # Section Header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Times-Bold',
        fontSize=18,
        leading=22,
        spaceBefore=20,
        spaceAfter=15,
        textColor=PRIMARY_COLOR
    ))
    
    # Subsection Header
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=10,
        textColor=ACCENT_COLOR
    ))
    
    # Body Text - Times New Roman, 12pt, 1.5 line spacing
    styles.add(ParagraphStyle(
        name='CustomBody',
        fontName='Times-Roman',
        fontSize=12,
        leading=18,  # 1.5 line spacing (12 * 1.5)
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=6
    ))
    
    # TOC Entry
    styles.add(ParagraphStyle(
        name='TOCEntry',
        fontName='Times-Roman',
        fontSize=12,
        leading=18,
        leftIndent=20,
        spaceBefore=3,
        spaceAfter=3
    ))
    
    # TOC Header
    styles.add(ParagraphStyle(
        name='TOCHeader',
        fontName='Times-Bold',
        fontSize=12,
        leading=18,
        spaceBefore=3,
        spaceAfter=3
    ))
    
    # Caption
    styles.add(ParagraphStyle(
        name='Caption',
        fontName='Times-Italic',
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        spaceBefore=5,
        spaceAfter=15,
        textColor=HexColor('#666666')
    ))
    
    return styles


def load_statistics():
    """Load statistics from database"""
    db_path = BASE_DIR / 'data' / 'processed' / 'articles.db'
    conn = sqlite3.connect(db_path)
    
    # Basic counts
    total_accepted = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    total_rejected = conn.execute("SELECT COUNT(*) FROM rejected").fetchone()[0]
    
    # Category distribution
    categories = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM articles GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    
    # AI techniques
    techniques = conn.execute(
        "SELECT ai_technique, COUNT(*) as cnt FROM articles GROUP BY ai_technique ORDER BY cnt DESC"
    ).fetchall()
    
    # Civil engineering areas
    areas = conn.execute(
        "SELECT civil_engineering_area, COUNT(*) as cnt FROM articles GROUP BY civil_engineering_area ORDER BY cnt DESC"
    ).fetchall()
    
    # Sources
    sources = conn.execute(
        "SELECT source_type, COUNT(*) as cnt FROM articles GROUP BY source_type ORDER BY cnt DESC"
    ).fetchall()
    
    conn.close()
    
    return {
        'total_accepted': total_accepted,
        'total_rejected': total_rejected,
        'total': total_accepted + total_rejected,
        'categories': categories[:10],
        'techniques': techniques[:10],
        'areas': areas[:10],
        'sources': sources
    }


def add_cover_page(story, styles):
    """Add cover page"""
    story.append(Spacer(1, 2*inch))
    
    story.append(Paragraph("FINAL PRESENTATION", styles['CoverTitle']))
    story.append(Spacer(1, 0.5*inch))
    
    story.append(Paragraph(
        "Artificial Intelligence Applications in Civil Engineering:",
        styles['CoverSubtitle']
    ))
    story.append(Paragraph(
        "A Comprehensive Analysis of Current Trends and Technologies",
        styles['CoverSubtitle']
    ))
    
    story.append(Spacer(1, 1*inch))
    
    # Decorative line
    story.append(Paragraph("_" * 50, styles['CoverSubtitle']))
    
    story.append(Spacer(1, 1*inch))
    
    story.append(Paragraph(
        f"Date: {datetime.now().strftime('%B %d, %Y')}",
        styles['CoverSubtitle']
    ))
    
    story.append(PageBreak())


def add_table_of_contents(story, styles):
    """Add table of contents"""
    story.append(Paragraph("TABLE OF CONTENTS", styles['SectionHeader']))
    story.append(Spacer(1, 0.3*inch))
    
    toc_entries = [
        ("1. Introduction", "3"),
        ("    1.1 Background", "3"),
        ("    1.2 Research Objectives", "3"),
        ("2. Methodology", "4"),
        ("    2.1 Data Collection", "4"),
        ("    2.2 Data Processing Pipeline", "4"),
        ("    2.3 LLM Classification", "5"),
        ("3. Analysis Results", "6"),
        ("    3.1 Category Distribution", "6"),
        ("    3.2 Time-based Trends", "7"),
        ("    3.3 Application Stage Analysis", "8"),
        ("    3.4 Keyword Analysis", "9"),
        ("    3.5 Source Analysis", "10"),
        ("    3.6 Time-Topic Relationship", "11"),
        ("    3.7 Civil Engineering Areas", "12"),
        ("    3.8 AI Techniques Distribution", "13"),
        ("4. Key Findings", "14"),
        ("5. Conclusion", "15"),
        ("References", "16"),
    ]
    
    for entry, page in toc_entries:
        dots = "." * (60 - len(entry) - len(page))
        story.append(Paragraph(f"{entry} {dots} {page}", styles['TOCEntry']))
    
    story.append(PageBreak())


def add_introduction(story, styles, stats):
    """Add introduction section"""
    story.append(Paragraph("1. INTRODUCTION", styles['SectionHeader']))
    
    story.append(Paragraph("1.1 Background", styles['SubsectionHeader']))
    
    intro_text = """
    The construction industry is undergoing a significant transformation driven by the integration 
    of Artificial Intelligence (AI) and Machine Learning (ML) technologies. These technologies 
    are revolutionizing traditional practices in civil engineering, from design optimization 
    to construction site safety monitoring and predictive maintenance. This research presents 
    a comprehensive analysis of how AI is being applied across various domains of civil 
    engineering, based on an extensive review of news articles and academic publications.
    """
    story.append(Paragraph(intro_text, styles['CustomBody']))
    
    story.append(Paragraph(
        f"""This study analyzed a total of <b>{stats['total']}</b> articles from various sources, 
        of which <b>{stats['total_accepted']}</b> ({stats['total_accepted']/stats['total']*100:.1f}%) 
        were identified as directly relevant to AI applications in civil engineering. 
        The remaining <b>{stats['total_rejected']}</b> articles were filtered out as they 
        discussed general construction topics without specific AI/ML applications.""",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("1.2 Research Objectives", styles['SubsectionHeader']))
    
    objectives = """
    The primary objectives of this research are:
    """
    story.append(Paragraph(objectives, styles['CustomBody']))
    
    obj_list = [
        "To identify and categorize AI applications in civil engineering",
        "To analyze temporal trends in AI adoption across different construction domains",
        "To determine which civil engineering areas are most impacted by AI technologies",
        "To identify the most prevalent AI techniques being utilized in the industry",
        "To provide insights into the future direction of AI in construction"
    ]
    
    for obj in obj_list:
        story.append(Paragraph(f"• {obj}", styles['CustomBody']))
    
    story.append(PageBreak())


def add_methodology(story, styles, stats):
    """Add methodology section"""
    story.append(Paragraph("2. METHODOLOGY", styles['SectionHeader']))
    
    story.append(Paragraph("2.1 Data Collection", styles['SubsectionHeader']))
    
    method_text = """
    Data was collected from multiple sources using a hybrid approach combining automated 
    collection methods:
    """
    story.append(Paragraph(method_text, styles['CustomBody']))
    
    # Data sources table
    source_data = [["Source Type", "Description", "Count"]]
    for src, cnt in stats['sources']:
        source_data.append([src, "News articles and academic papers", str(cnt)])
    
    table = Table(source_data, colWidths=[2*inch, 3*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("2.2 Data Processing Pipeline", styles['SubsectionHeader']))
    
    pipeline_text = """
    The data processing pipeline consisted of the following stages:
    """
    story.append(Paragraph(pipeline_text, styles['CustomBody']))
    
    pipeline_steps = [
        "<b>RSS Feed Collection:</b> Automated collection from 16+ industry RSS feeds including Google News",
        "<b>API Integration:</b> News collected from GNews API, NewsAPI, and The Guardian API",
        "<b>Academic Sources:</b> Google Scholar papers collected via SerpAPI",
        "<b>Deduplication:</b> URL-based and title-based deduplication to ensure unique articles",
        "<b>Data Validation:</b> Quality checks for missing fields and data integrity"
    ]
    
    for step in pipeline_steps:
        story.append(Paragraph(f"• {step}", styles['CustomBody']))
    
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("2.3 LLM Classification", styles['SubsectionHeader']))
    
    llm_text = """
    Each article was processed using Google's Gemini 2.0 Flash large language model for 
    intelligent classification. The LLM performed the following tasks:
    """
    story.append(Paragraph(llm_text, styles['CustomBody']))
    
    llm_tasks = [
        "<b>Relevance Filtering:</b> Determining if the article discusses actual AI/ML applications",
        "<b>Category Classification:</b> Assigning primary application category (Safety, BIM, etc.)",
        "<b>CE Area Identification:</b> Identifying the civil engineering domain",
        "<b>AI Technique Extraction:</b> Determining the AI/ML technique discussed",
        "<b>Keyword Generation:</b> Extracting relevant keywords for analysis",
        "<b>Summary Generation:</b> Creating concise article summaries"
    ]
    
    for task in llm_tasks:
        story.append(Paragraph(f"• {task}", styles['CustomBody']))
    
    story.append(PageBreak())


def add_analysis_section(story, styles, stats):
    """Add analysis results section with visualizations"""
    story.append(Paragraph("3. ANALYSIS RESULTS", styles['SectionHeader']))
    
    # 3.1 Category Distribution
    story.append(Paragraph("3.1 Category Distribution Analysis", styles['SubsectionHeader']))
    
    cat_text = """
    The analysis of category distribution reveals the primary areas where AI is being 
    applied in civil engineering. The following chart illustrates the distribution of 
    articles across different application categories:
    """
    story.append(Paragraph(cat_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '1_category_distribution.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 1: Distribution of AI applications by category", styles['Caption']))
    
    # Category findings
    if stats['categories']:
        top_cat = stats['categories'][0]
        story.append(Paragraph(
            f"""The most prominent category is <b>{top_cat[0]}</b> with {top_cat[1]} articles, 
            followed by {stats['categories'][1][0]} ({stats['categories'][1][1]} articles) 
            and {stats['categories'][2][0]} ({stats['categories'][2][1]} articles).""",
            styles['CustomBody']
        ))
    
    story.append(PageBreak())
    
    # 3.2 Time Trends
    story.append(Paragraph("3.2 Time-based Trend Analysis", styles['SubsectionHeader']))
    
    trend_text = """
    Temporal analysis provides insights into how AI adoption in civil engineering has evolved 
    over time. The following visualization shows publication trends:
    """
    story.append(Paragraph(trend_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '2_time_trends.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=4.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 2: Publication trends over time showing overall and category-specific patterns", styles['Caption']))
    
    story.append(PageBreak())
    
    # 3.3 Application Stage
    story.append(Paragraph("3.3 Application Stage Analysis", styles['SubsectionHeader']))
    
    stage_text = """
    This analysis examines at which stage of the construction project lifecycle AI 
    technologies are being applied:
    """
    story.append(Paragraph(stage_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '3_application_stage.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 3: AI applications across project lifecycle stages", styles['Caption']))
    
    story.append(PageBreak())
    
    # 3.4 Keywords
    story.append(Paragraph("3.4 Keyword Analysis", styles['SubsectionHeader']))
    
    kw_text = """
    Keyword analysis reveals the most frequently discussed terms and concepts in 
    AI-related civil engineering literature:
    """
    story.append(Paragraph(kw_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '4_keywords.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 4: Top keywords and word cloud visualization", styles['Caption']))
    
    story.append(PageBreak())
    
    # 3.5 Sources
    story.append(Paragraph("3.5 Source Analysis", styles['SubsectionHeader']))
    
    src_text = """
    Analysis of data sources helps understand the origin and reliability of the 
    collected information:
    """
    story.append(Paragraph(src_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '5_sources.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 5: Distribution of articles by source", styles['Caption']))
    
    story.append(PageBreak())
    
    # 3.6 Time-Topic Heatmap
    story.append(Paragraph("3.6 Time-Topic Relationship", styles['SubsectionHeader']))
    
    hm_text = """
    The heatmap visualization shows how different topics have evolved over time, 
    revealing emerging trends and shifting focus areas:
    """
    story.append(Paragraph(hm_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '6_time_topic_heatmap.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=4*inch)
        story.append(img)
        story.append(Paragraph("Figure 6: Heatmap showing topic evolution over time", styles['Caption']))
    
    story.append(PageBreak())
    
    # 3.7 Civil Engineering Areas
    story.append(Paragraph("3.7 Civil Engineering Areas Analysis", styles['SubsectionHeader']))
    
    ce_text = """
    This analysis examines which civil engineering disciplines are most impacted by 
    AI technologies:
    """
    story.append(Paragraph(ce_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '7_civil_eng_areas.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 7: AI applications across civil engineering disciplines", styles['Caption']))
    
    if stats['areas']:
        top_area = stats['areas'][0]
        story.append(Paragraph(
            f"""<b>{top_area[0]}</b> emerges as the leading area with {top_area[1]} articles, 
            indicating significant AI adoption in project management and field operations.""",
            styles['CustomBody']
        ))
    
    story.append(PageBreak())
    
    # 3.8 AI Techniques
    story.append(Paragraph("3.8 AI Techniques Distribution", styles['SubsectionHeader']))
    
    ai_text = """
    Analysis of AI techniques reveals which machine learning and artificial intelligence 
    methods are most commonly applied in civil engineering:
    """
    story.append(Paragraph(ai_text, styles['CustomBody']))
    
    img_path = VIZ_DIR / '8_ai_techniques.png'
    if img_path.exists():
        img = Image(str(img_path), width=6*inch, height=3.5*inch)
        story.append(img)
        story.append(Paragraph("Figure 8: Distribution of AI techniques used in civil engineering", styles['Caption']))
    
    if stats['techniques']:
        top_tech = stats['techniques'][0]
        story.append(Paragraph(
            f"""<b>{top_tech[0]}</b> is the most prevalent technique with {top_tech[1]} applications, 
            followed by {stats['techniques'][1][0]} ({stats['techniques'][1][1]} articles).""",
            styles['CustomBody']
        ))
    
    story.append(PageBreak())


def add_findings(story, styles, stats):
    """Add key findings section"""
    story.append(Paragraph("4. KEY FINDINGS", styles['SectionHeader']))
    
    findings_text = """
    Based on the comprehensive analysis of {total} articles, the following key findings 
    have been identified:
    """.format(total=stats['total'])
    story.append(Paragraph(findings_text, styles['CustomBody']))
    
    findings = [
        f"<b>High AI Relevance:</b> {stats['total_accepted']/stats['total']*100:.1f}% of analyzed articles were directly relevant to AI applications in civil engineering, indicating significant industry interest.",
        
        f"<b>Dominant Application Area:</b> {stats['categories'][0][0] if stats['categories'] else 'N/A'} emerged as the primary category, suggesting strong focus on construction operations and automation.",
        
        f"<b>Leading AI Technique:</b> {stats['techniques'][0][0] if stats['techniques'] else 'N/A'} is the most widely applied AI method, followed by robotics and automation solutions.",
        
        f"<b>Construction Management Focus:</b> {stats['areas'][0][0] if stats['areas'] else 'N/A'} represents the primary civil engineering domain benefiting from AI integration.",
        
        "<b>Safety Applications:</b> AI-powered safety monitoring and hazard detection systems are gaining significant attention in the industry.",
        
        "<b>BIM Integration:</b> Building Information Modeling enhanced with AI capabilities represents a growing trend in design and planning phases.",
        
        "<b>Predictive Analytics:</b> Predictive maintenance and cost estimation using ML models are becoming increasingly common.",
        
        "<b>Computer Vision:</b> Image and video analysis for quality control and site monitoring is a rapidly advancing application area."
    ]
    
    for finding in findings:
        story.append(Paragraph(f"• {finding}", styles['CustomBody']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())


def add_conclusion(story, styles, stats):
    """Add conclusion section"""
    story.append(Paragraph("5. CONCLUSION", styles['SectionHeader']))
    
    conclusion_text = f"""
    This comprehensive analysis of {stats['total']} articles reveals that Artificial Intelligence 
    is rapidly transforming the civil engineering and construction industry. With 
    {stats['total_accepted']} ({stats['total_accepted']/stats['total']*100:.1f}%) articles 
    directly addressing AI/ML applications, it is evident that the industry is actively 
    embracing these technologies.
    """
    story.append(Paragraph(conclusion_text, styles['CustomBody']))
    
    story.append(Paragraph(
        """The research demonstrates that AI applications span across all phases of the 
        construction project lifecycle, from planning and design to construction operations 
        and maintenance. Machine Learning and Robotics emerge as the dominant techniques, 
        while Construction Management benefits most from these technological advances.""",
        styles['CustomBody']
    ))
    
    story.append(Paragraph(
        """Looking forward, the trends indicate continued growth in AI adoption, particularly 
        in areas such as safety monitoring, predictive maintenance, and automated quality 
        control. The integration of Computer Vision and Deep Learning technologies is 
        expected to further revolutionize on-site operations and project management practices.""",
        styles['CustomBody']
    ))
    
    story.append(Paragraph("Future Research Directions", styles['SubsectionHeader']))
    
    future_text = """
    Based on the findings, the following areas merit further investigation:
    """
    story.append(Paragraph(future_text, styles['CustomBody']))
    
    future_items = [
        "Integration of generative AI in structural design optimization",
        "Development of comprehensive AI frameworks for construction safety",
        "Advancement of autonomous construction equipment and robotics",
        "AI-driven sustainability analysis and environmental impact assessment",
        "Real-time decision support systems for project management"
    ]
    
    for item in future_items:
        story.append(Paragraph(f"• {item}", styles['CustomBody']))
    
    story.append(PageBreak())
    
    # References
    story.append(Paragraph("REFERENCES", styles['SectionHeader']))
    
    refs_text = """
    Data sources and APIs used in this research:
    """
    story.append(Paragraph(refs_text, styles['CustomBody']))
    
    references = [
        "Google News RSS Feeds - news.google.com",
        "GNews API - gnews.io",
        "NewsAPI - newsapi.org", 
        "The Guardian API - open-platform.theguardian.com",
        "Google Scholar via SerpAPI - serpapi.com",
        "Google Gemini 2.0 Flash - ai.google.dev"
    ]
    
    for i, ref in enumerate(references, 1):
        story.append(Paragraph(f"[{i}] {ref}", styles['CustomBody']))


def add_page_number(canvas, doc):
    """Add page numbers"""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Times-Roman', 10)
    canvas.drawCentredString(A4[0]/2, 0.5*inch, text)
    canvas.restoreState()


def main():
    """Generate the PDF report"""
    print("="*60)
    print("GENERATING FINAL REPORT PDF")
    print("="*60)
    
    # Load statistics
    print("Loading statistics...")
    stats = load_statistics()
    print(f"  Total articles: {stats['total']}")
    print(f"  Accepted: {stats['total_accepted']}")
    
    # Create document
    print("Creating PDF document...")
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    # Create styles
    styles = create_styles()
    
    # Build story
    story = []
    
    print("Adding cover page...")
    add_cover_page(story, styles)
    
    print("Adding table of contents...")
    add_table_of_contents(story, styles)
    
    print("Adding introduction...")
    add_introduction(story, styles, stats)
    
    print("Adding methodology...")
    add_methodology(story, styles, stats)
    
    print("Adding analysis sections...")
    add_analysis_section(story, styles, stats)
    
    print("Adding key findings...")
    add_findings(story, styles, stats)
    
    print("Adding conclusion...")
    add_conclusion(story, styles, stats)
    
    # Build PDF
    print("Building PDF...")
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    print()
    print("="*60)
    print(f"✅ PDF GENERATED: {PDF_PATH}")
    print("="*60)


if __name__ == "__main__":
    main()
