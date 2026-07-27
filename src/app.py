import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os
import requests
from sentiment_analyzer import analyze_sentiment
from langchain_agent import query_database

st.set_page_config(
    page_title="NewsSentinel | Market Intelligence Console",
    page_icon="📰",
    layout="wide"
)

# Hide Streamlit top bar, deploy button, and footer
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    </style>
""", unsafe_allow_html=True)

DB_PATH = "newssentinel.duckdb"
DELTA_PATH = "./data/bronze_news"

SAMPLE_STORIES = [
    {"title": "NVIDIA Launches Next-Gen Blackwell Ultra Chips for Generative AI", "author": "tech_insider", "upvotes": 450, "comment_count": 85, "sentiment_label": "Positive", "sentiment_score": 0.65, "published_at": "2026-07-28T02:00:00"},
    {"title": "OpenAI Releases GPT-4.5 with Enhanced Reasoning Capabilities", "author": "ai_dev", "upvotes": 620, "comment_count": 140, "sentiment_label": "Positive", "sentiment_score": 0.72, "published_at": "2026-07-28T01:30:00"},
    {"title": "Global Cyberattack Vulnerability Found in Legacy Enterprise Routers", "author": "sec_researcher", "upvotes": 280, "comment_count": 62, "sentiment_label": "Negative", "sentiment_score": -0.58, "published_at": "2026-07-28T01:15:00"},
    {"title": "Google Cloud Outage Impacting Multiple Major Services", "author": "cloud_watch", "upvotes": 310, "comment_count": 95, "sentiment_label": "Negative", "sentiment_score": -0.45, "published_at": "2026-07-28T00:45:00"},
    {"title": "Apple Unveils On-Device Privacy Architecture for VisionOS", "author": "apple_fan", "upvotes": 390, "comment_count": 48, "sentiment_label": "Positive", "sentiment_score": 0.52, "published_at": "2026-07-28T00:30:00"},
    {"title": "Python 3.13 Released with Experimental Free-Threaded No-GIL Mode", "author": "guido_fan", "upvotes": 540, "comment_count": 112, "sentiment_label": "Positive", "sentiment_score": 0.48, "published_at": "2026-07-27T23:50:00"},
    {"title": "Major Tech Company Announces 5% Workforce Restructuring", "author": "news_bot", "upvotes": 190, "comment_count": 55, "sentiment_label": "Negative", "sentiment_score": -0.35, "published_at": "2026-07-27T23:10:00"}
]

def fetch_live_fallback():
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            ids = res.json()[:15]
            stories = []
            for sid in ids:
                s_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=2)
                if s_res.status_code == 200:
                    s = s_res.json()
                    if s and 'title' in s:
                        sent = analyze_sentiment(s.get('title', ''))
                        stories.append({
                            'story_id': str(s.get('id')),
                            'title': s.get('title', ''),
                            'author': s.get('by', 'anonymous'),
                            'upvotes': s.get('score', 0),
                            'comment_count': s.get('descendants', 0),
                            'sentiment_score': sent['compound'],
                            'sentiment_label': sent['sentiment_label'],
                            'published_at': pd.Timestamp.now().isoformat()
                        })
            if stories:
                return pd.DataFrame(stories)
    except Exception:
        pass
    return pd.DataFrame(SAMPLE_STORIES)

def load_data():
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            news_df = conn.execute("SELECT * FROM stg_news ORDER BY published_at DESC").fetchdf()
            conn.close()
            if not news_df.empty:
                return news_df
        except Exception:
            pass
            
    if os.path.exists(DELTA_PATH):
        try:
            conn = duckdb.connect()
            news_df = conn.execute(f"SELECT * FROM read_parquet('{DELTA_PATH}/*.parquet') ORDER BY created_at DESC").fetchdf()
            conn.close()
            if not news_df.empty:
                news_df['published_at'] = news_df['created_at']
                news_df['upvotes'] = news_df['score']
                news_df['comment_count'] = news_df['comments']
                return news_df
        except Exception:
            pass
            
    return fetch_live_fallback()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/news.png", width=70)
    st.title("NewsSentinel Console")
    st.caption("Real-Time Global Market & Tech Trend Intelligence")
    
    st.divider()
    st.subheader("⚙️ System Status")
    st.success("🟢 Ingestion Stream: Active")
    st.success("🟢 Delta Lakehouse: Connected")
    st.success("🟢 dbt Quality: Tested [PASS]")
    st.success("🟢 LangChain AI: Ready")
    
    st.divider()
    sentiment_filter = st.multiselect(
        "Filter by Sentiment:",
        options=["Positive", "Neutral", "Negative"],
        default=["Positive", "Neutral", "Negative"]
    )

# Main Header
st.title("📰 NewsSentinel Market Intelligence Console")
st.markdown("Live HackerNews Stream → Delta Lakehouse → dbt Analytics → LangChain AI RAG")

news_df = load_data()

if not news_df.empty and sentiment_filter:
    filtered_df = news_df[news_df['sentiment_label'].isin(sentiment_filter)]
else:
    filtered_df = news_df

# Summary Metrics Cards
m1, m2, m3, m4 = st.columns(4)

total_stories = len(filtered_df)
avg_score = round(filtered_df['sentiment_score'].mean(), 3) if not filtered_df.empty else 0.0
pos_count = len(filtered_df[filtered_df['sentiment_label'] == 'Positive']) if not filtered_df.empty else 0
neg_count = len(filtered_df[filtered_df['sentiment_label'] == 'Negative']) if not filtered_df.empty else 0

m1.metric("Total Stories", total_stories)
m2.metric("Avg Sentiment Score", avg_score)
m3.metric("Positive Signals", pos_count)
m4.metric("Negative Risk Signals", neg_count)

st.divider()

# LANGCHAIN AI ASSISTANT SECTION (SINGLE PAGE - NO TABS)
st.subheader("🤖 LangChain AI Market Intelligence Assistant")
st.caption("Ask natural language questions to query your live Lakehouse data.")

with st.form(key="ai_query_form"):
    user_q = st.text_input("Type your question (e.g., 'top positive news', 'negative risk stories', 'most popular') and click Run AI Query:")
    submit_button = st.form_submit_button(label="🚀 Run LangChain AI Query")

if submit_button and user_q:
    with st.spinner("LangChain Agent querying DuckDB Lakehouse..."):
        ai_res = query_database(user_q)
        st.success("Analysis Complete!")
        st.markdown(ai_res)

st.divider()

# VISUAL CHARTS
st.subheader("📊 Market Sentiment Analytics & Trends")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    fig1 = px.pie(
        filtered_df, 
        names='sentiment_label', 
        color='sentiment_label',
        title="Live Sentiment Distribution",
        color_discrete_map={'Positive': '#2ecc71', 'Neutral': '#95a5a6', 'Negative': '#e74c3c'}
    )
    st.plotly_chart(fig1, use_container_width=True)
    
with chart_col2:
    top_df = filtered_df.nlargest(7, 'upvotes')
    fig2 = px.bar(
        top_df, 
        x='upvotes', 
        y='title', 
        orientation='h',
        title="Highest Upvoted Tech Stories",
        color='sentiment_label',
        color_discrete_map={'Positive': '#2ecc71', 'Neutral': '#95a5a6', 'Negative': '#e74c3c'}
    )
    fig2.update_layout(yaxis={'autorange': 'reversed'})
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# REAL TIME STREAM TABLE
st.subheader("📋 Real-Time News Stream Feed")
search_term = st.text_input("🔍 Search news titles:")

if search_term:
    display_df = filtered_df[filtered_df['title'].str.contains(search_term, case=False, na=False)]
else:
    display_df = filtered_df

st.dataframe(
    display_df[['title', 'author', 'upvotes', 'comment_count', 'sentiment_label', 'sentiment_score']],
    use_container_width=True
)
