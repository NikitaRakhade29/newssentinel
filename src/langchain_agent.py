import os
import re
import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = "newssentinel.duckdb"
DELTA_PATH = "./data/bronze_news"

DEFAULT_STORIES = [
    {"title": "NVIDIA Launches Next-Gen Blackwell Ultra Chips for Generative AI", "author": "tech_insider", "upvotes": 450, "sentiment_label": "Positive", "sentiment_score": 0.65},
    {"title": "OpenAI Releases GPT-4.5 with Enhanced Reasoning Capabilities", "author": "ai_dev", "upvotes": 620, "sentiment_label": "Positive", "sentiment_score": 0.72},
    {"title": "Global Cyberattack Vulnerability Found in Legacy Enterprise Routers", "author": "sec_researcher", "upvotes": 280, "sentiment_label": "Negative", "sentiment_score": -0.58},
    {"title": "Google Cloud Outage Impacting Multiple Major Services", "author": "cloud_watch", "upvotes": 310, "sentiment_label": "Negative", "sentiment_score": -0.45},
    {"title": "Apple Unveils On-Device Privacy Architecture for VisionOS", "author": "apple_fan", "upvotes": 390, "sentiment_label": "Positive", "sentiment_score": 0.52},
    {"title": "Python 3.13 Released with Experimental Free-Threaded No-GIL Mode", "author": "guido_fan", "upvotes": 540, "sentiment_label": "Positive", "sentiment_score": 0.48},
    {"title": "Major Tech Company Announces 5% Workforce Restructuring", "author": "news_bot", "upvotes": 190, "sentiment_label": "Negative", "sentiment_score": -0.35}
]

def load_all_stories():
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            df = conn.execute("SELECT * FROM stg_news ORDER BY published_at DESC").fetchdf()
            conn.close()
            if not df.empty:
                return df
        except Exception:
            pass
            
    if os.path.exists(DELTA_PATH):
        try:
            conn = duckdb.connect()
            df = conn.execute(f"SELECT * FROM read_parquet('{DELTA_PATH}/*.parquet') ORDER BY created_at DESC").fetchdf()
            conn.close()
            if not df.empty:
                df['upvotes'] = df['score']
                return df
        except Exception:
            pass
            
    return pd.DataFrame(DEFAULT_STORIES)

def match_topic_word(title, query):
    # Fix substring bug: match whole words using regex word boundaries
    if query.lower() == 'ai':
        pattern = r'\b(ai|llm|gpt|openai|claude|gemini|machine learning|artificial intelligence|model|models)\b'
    else:
        pattern = r'\b' + re.escape(query.lower()) + r'\b'
    return bool(re.search(pattern, title.lower()))

def query_database(user_query):
    query_str = user_query.strip()
    query_lower = query_str.lower()
    
    df = load_all_stories()
    if df.empty:
        df = pd.DataFrame(DEFAULT_STORIES)
        
    # Search logic
    if "positive" in query_lower:
        matched = df[df['sentiment_label'] == 'Positive']
    elif "negative" in query_lower or "risk" in query_lower:
        matched = df[df['sentiment_label'] == 'Negative']
    elif "top" in query_lower or "popular" in query_lower or "upvote" in query_lower:
        matched = df.sort_values('upvotes', ascending=False)
    else:
        # Use regex word boundary matching to avoid matching 'braid' or 'faithful' for 'AI'
        matched = df[df['title'].apply(lambda t: match_topic_word(t, query_str))]
        
    is_fallback = False
    if matched.empty:
        matched = df.sort_values('upvotes', ascending=False).head(5)
        is_fallback = True

    filtered = matched.head(5)
    
    rows = []
    for idx, (_, r) in enumerate(filtered.iterrows(), start=1):
        upvotes_val = r.get('upvotes', r.get('score', 100))
        label_str = "Positive Market Signal" if r['sentiment_label'] == 'Positive' else ("Negative Risk Factor" if r['sentiment_label'] == 'Negative' else "Neutral Tech News")
        rows.append(f"{idx}. [{label_str}] {r['title']} (Upvotes: {upvotes_val})")
        
    summary_text = "\n".join(rows)
    
    if is_fallback:
        header = f"No direct stories matching '{query_str}' in live stream. Showing top trending tech news:\n"
    else:
        header = f"Market Intelligence Briefing for '{query_str}':\n"
        
    final_output = f"{header}\n{summary_text}"
    
    if GEMINI_KEY and GEMINI_KEY != "your_free_gemini_api_key_here":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain.prompts import PromptTemplate

            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_KEY)
            prompt = PromptTemplate(
                input_variables=["query", "data"],
                template="You are NewsSentinel AI Market Analyst. Rewrite the following market findings into clean, professional, human-readable bullet sentences.\n\nQuery: {query}\n\nData:\n{data}\n\nSummary:"
            )
            res = (prompt | llm).invoke({"query": query_str, "data": summary_text})
            clean_res = res.content.replace("**", "").replace("###", "").replace("*", "")
            return clean_res
        except Exception:
            pass
            
    return final_output

if __name__ == "__main__":
    print(query_database("AI"))
