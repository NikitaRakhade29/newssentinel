import os
import duckdb
import pandas as pd
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sentiment_analyzer import analyze_sentiment
from langchain_agent import query_database

load_dotenv()

app = FastAPI(
    title="NewsSentinel API",
    description="Real-Time Global Market & Tech Trend Intelligence Platform API",
    version="1.0.0"
)

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

class AIQueryRequest(BaseModel):
    query: str

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

@app.get("/api/stories")
def get_stories(limit: int = 50, sentiment: str = None):
    df = load_data()
    if df.empty:
        return {"stories": [], "count": 0}
    
    if sentiment and sentiment.lower() != 'all':
        df = df[df['sentiment_label'].str.lower() == sentiment.lower()]
        
    records = df.head(limit).to_dict(orient="records")
    return {"stories": records, "count": len(records)}

@app.get("/api/analytics")
def get_analytics():
    df = load_data()
    if df.empty:
        return {"total_stories": 0, "avg_sentiment": 0, "positive": 0, "neutral": 0, "negative": 0}
    
    counts = df['sentiment_label'].value_counts().to_dict()
    return {
        "total_stories": len(df),
        "avg_sentiment": round(float(df['sentiment_score'].mean()), 3),
        "positive": counts.get("Positive", 0),
        "neutral": counts.get("Neutral", 0),
        "negative": counts.get("Negative", 0)
    }

@app.post("/api/ai-query")
def ai_query(req: AIQueryRequest):
    answer = query_database(req.query)
    return {"query": req.query, "answer": answer}

@app.get("/", response_class=HTMLResponse)
def dashboard_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NewsSentinel | Market Intelligence Console</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #0e1117; color: #fafafa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .card { background-color: #161b22; border: 1px solid #30363d; color: #fafafa; border-radius: 8px; }
            .metric-val { font-size: 2rem; font-weight: bold; }
            .badge-pos { background-color: #2ecc71; }
            .badge-neu { background-color: #95a5a6; }
            .badge-neg { background-color: #e74c3c; }
        </style>
    </head>
    <body class="p-4">
        <div class="container-fluid">
            <!-- Header -->
            <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary">
                <div>
                    <h2>📰 NewsSentinel Market Intelligence Console</h2>
                    <p class="text-secondary mb-0">HackerNews Live Stream &rarr; Delta Lakehouse &rarr; dbt Analytics &rarr; LangChain AI RAG</p>
                </div>
                <div>
                    <button onclick="refreshDashboard()" class="btn btn-primary">🔄 Refresh Live Data</button>
                </div>
            </div>

            <!-- Metric Cards -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card p-3">
                        <small class="text-secondary">Total Live Stories</small>
                        <div id="m-total" class="metric-val text-info">0</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3">
                        <small class="text-secondary">Avg Sentiment Score</small>
                        <div id="m-avg" class="metric-val text-primary">0.0</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3">
                        <small class="text-secondary">Positive Signals</small>
                        <div id="m-pos" class="metric-val text-success">0</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3">
                        <small class="text-secondary">Negative Risk Signals</small>
                        <div id="m-neg" class="metric-val text-danger">0</div>
                    </div>
                </div>
            </div>

            <!-- PROMINENT LANGCHAIN AI SECTION ON MAIN PAGE -->
            <div class="card p-4 mb-4 border-primary">
                <h4>🤖 LangChain AI Market Intelligence Assistant</h4>
                <p class="text-secondary">Ask natural language questions to query your live Lakehouse data (e.g., 'top positive news', 'negative risk stories', 'most popular').</p>
                
                <div class="mb-3">
                    <button onclick="runQuickQuery('Show top positive tech news')" class="btn btn-outline-success me-2">💡 Top Positive News</button>
                    <button onclick="runQuickQuery('Show negative stories')" class="btn btn-outline-danger me-2">⚠️ Negative Risk Stories</button>
                    <button onclick="runQuickQuery('Show top upvoted tech news')" class="btn btn-outline-warning">🔥 Most Popular Stories</button>
                </div>

                <div class="input-group mb-3">
                    <input type="text" id="aiInput" class="form-control bg-dark text-light border-secondary" placeholder="Type your query and click Ask LangChain AI...">
                    <button onclick="sendAIQuery()" class="btn btn-primary">Ask LangChain AI</button>
                </div>

                <div id="aiResult" class="p-3 card bg-dark text-light d-none border-success" style="white-space: pre-wrap; font-size: 1.05rem;"></div>
            </div>

            <!-- Real-Time News Stream Feed -->
            <div class="card p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4>📋 Real-Time News Stream Feed</h4>
                    <input type="text" id="searchInput" onkeyup="filterTable()" class="form-control bg-dark text-light border-secondary w-25" placeholder="🔍 Search news titles...">
                </div>
                <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle" id="newsTable">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>Author</th>
                                <th>Upvotes</th>
                                <th>Comments</th>
                                <th>Sentiment</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody id="newsTbody">
                            <tr><td colspan="6" class="text-center text-secondary">Loading live news feed...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"></script>
        <script>
            let allStories = [];

            async function refreshDashboard() {
                try {
                    const aRes = await fetch('/api/analytics');
                    const analytics = await aRes.json();
                    
                    document.getElementById('m-total').innerText = analytics.total_stories;
                    document.getElementById('m-avg').innerText = analytics.avg_sentiment;
                    document.getElementById('m-pos').innerText = analytics.positive;
                    document.getElementById('m-neg').innerText = analytics.negative;

                    const sRes = await fetch('/api/stories?limit=50');
                    const data = await sRes.json();
                    allStories = data.stories;
                    renderTable(allStories);
                } catch(e) {
                    console.error(e);
                }
            }

            function renderTable(stories) {
                const tbody = document.getElementById('newsTbody');
                if(!stories || stories.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary">No stories available.</td></tr>';
                    return;
                }
                tbody.innerHTML = stories.map(s => {
                    let badgeClass = 'badge-neu';
                    if(s.sentiment_label === 'Positive') badgeClass = 'badge-pos';
                    if(s.sentiment_label === 'Negative') badgeClass = 'badge-neg';
                    return `<tr>
                        <td><strong>${s.title}</strong></td>
                        <td>${s.author}</td>
                        <td>${s.upvotes}</td>
                        <td>${s.comment_count}</td>
                        <td><span class="badge ${badgeClass}">${s.sentiment_label}</span></td>
                        <td>${s.sentiment_score}</td>
                    </tr>`;
                }).join('');
            }

            function filterTable() {
                const term = document.getElementById('searchInput').value.toLowerCase();
                const filtered = allStories.filter(s => s.title.toLowerCase().includes(term));
                renderTable(filtered);
            }

            function runQuickQuery(q) {
                document.getElementById('aiInput').value = q;
                sendAIQuery();
            }

            async function sendAIQuery() {
                const q = document.getElementById('aiInput').value;
                if(!q) return;
                const resultDiv = document.getElementById('aiResult');
                resultDiv.classList.remove('d-none');
                resultDiv.innerText = "🤖 LangChain Agent querying DuckDB Lakehouse...";
                
                try {
                    const res = await fetch('/api/ai-query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: q})
                    });
                    const data = await res.json();
                    resultDiv.innerText = data.answer;
                } catch(e) {
                    resultDiv.innerText = "Error executing AI query: " + e;
                }
            }

            refreshDashboard();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 NewsSentinel FastAPI Server Running!")
    print("👉 Open Dashboard in Browser: http://127.0.0.1:8000")
    print("👉 Open API Specs (/docs):    http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
