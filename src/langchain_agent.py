import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = "newssentinel.duckdb"
DELTA_PATH = "./data/bronze_news"

SAMPLE_STORIES = [
    {"title": "NVIDIA Launches Next-Gen Blackwell Ultra Chips for Generative AI", "author": "tech_insider", "upvotes": 450, "sentiment_label": "Positive", "sentiment_score": 0.65},
    {"title": "OpenAI Releases GPT-4.5 with Enhanced Reasoning Capabilities", "author": "ai_dev", "upvotes": 620, "sentiment_label": "Positive", "sentiment_score": 0.72},
    {"title": "Global Cyberattack Vulnerability Found in Legacy Enterprise Routers", "author": "sec_researcher", "upvotes": 280, "sentiment_label": "Negative", "sentiment_score": -0.58},
    {"title": "Google Cloud Outage Impacting Multiple Major Services", "author": "cloud_watch", "upvotes": 310, "sentiment_label": "Negative", "sentiment_score": -0.45},
    {"title": "Apple Unveils On-Device Privacy Architecture for VisionOS", "author": "apple_fan", "upvotes": 390, "sentiment_label": "Positive", "sentiment_score": 0.52},
    {"title": "Python 3.13 Released with Experimental Free-Threaded No-GIL Mode", "author": "guido_fan", "upvotes": 540, "sentiment_label": "Positive", "sentiment_score": 0.48},
    {"title": "Major Tech Company Announces 5% Workforce Restructuring", "author": "news_bot", "upvotes": 190, "sentiment_label": "Negative", "sentiment_score": -0.35}
]

def query_database(user_query):
    query_str = user_query.strip()
    query_lower = query_str.lower()
    
    # Load dataset from DuckDB, Delta Lake, or Sample
    df = pd.DataFrame()
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            df = conn.execute("SELECT * FROM stg_news").fetchdf()
            conn.close()
        except Exception:
            pass
            
    if df.empty and os.path.exists(DELTA_PATH):
        try:
            conn = duckdb.connect()
            df = conn.execute(f"SELECT * FROM read_parquet('{DELTA_PATH}/*.parquet')").fetchdf()
            conn.close()
            if not df.empty:
                df['upvotes'] = df['score']
        except Exception:
            pass
            
    if df.empty:
        df = pd.DataFrame(SAMPLE_STORIES)
        
    # Search logic: check exact keyword in title first
    if "positive" in query_lower:
        filtered = df[df['sentiment_label'] == 'Positive'].sort_values('upvotes', ascending=False).head(5)
    elif "negative" in query_lower or "risk" in query_lower:
        filtered = df[df['sentiment_label'] == 'Negative'].sort_values('upvotes', ascending=False).head(5)
    elif "top" in query_lower or "popular" in query_lower or "upvote" in query_lower:
        filtered = df.sort_values('upvotes', ascending=False).head(5)
    else:
        # Search title for user keyword
        matched = df[df['title'].str.contains(query_lower, case=False, na=False)]
        if not matched.empty:
            filtered = matched.sort_values('upvotes', ascending=False).head(5)
        else:
            return f"No news stories found matching keyword '{query_str}'.\n\nTry searching for topics like: 'AI', 'NVIDIA', 'Cloud', 'Apple', 'Python', 'Positive', 'Negative', or 'Top News'."
            
    rows = []
    for idx, (_, r) in enumerate(filtered.iterrows(), start=1):
        label_str = "Positive Market Signal" if r['sentiment_label'] == 'Positive' else ("Negative Risk Factor" if r['sentiment_label'] == 'Negative' else "Neutral Insight")
        rows.append(f"{idx}. [{label_str}] {r['title']} (Community Engagement: {r['upvotes']} upvotes).")
        
    summary_text = "\n".join(rows)
    
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
            
    return f"Market Intelligence Briefing for '{query_str}':\n\n{summary_text}"

if __name__ == "__main__":
    print(query_database("moon"))
    print("---")
    print(query_database("AI"))
