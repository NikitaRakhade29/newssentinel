# NewsSentinel: Real-Time Market & Tech Trend Intelligence Platform

NewsSentinel is a real-time streaming data platform that ingests live tech stories from HackerNews, stores them in a local Delta Lakehouse, cleans and transforms them using dbt, analyzes sentiment with VADER NLP, and provides natural-language market intelligence through a LangChain AI RAG Agent served over a FastAPI web application.

## System Architecture

```
[HackerNews Live API] -> [Kafka (Docker)] -> [Delta Lake] -> [dbt + DuckDB] -> [VADER NLP & LangChain] -> [FastAPI Web Console]
```

## Problem Solved

Market analysts, product teams, and investors face information overload from thousands of tech articles and company announcements published daily. NewsSentinel solves this by:
1. Continuous ingestion of live tech news without manual monitoring.
2. Real-time sentiment scoring (Positive, Neutral, Negative) to spot emerging hype cycles or public backlash.
3. Conversational AI querying via LangChain so analysts can ask natural questions instead of writing SQL.

---

## Step-by-Step Setup Guide

### 1. Prerequisites
- Python 3.11+
- Docker Desktop

### 2. Environment Setup
Clone or navigate to the project directory:
```bash
cd C:\Users\HP\.gemini\antigravity\scratch\newssentinel
```

Create and activate virtual environment:
```bash
python -m venv venv

# Windows PowerShell / CMD:
.\venv\Scripts\activate

# Mac / Linux:
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up environment file:
```bash
cp .env.example .env
```
*(Optional: Add your free Google Gemini API key to `.env` if available)*

### 3. Start Local Kafka Broker
```bash
docker compose up -d
```

### 4. Run Live Data Ingestion
Open **Terminal 1**:
```bash
python src/hackernews_producer.py
```

Open **Terminal 2**:
```bash
python src/lakehouse_consumer.py
```

### 5. Run dbt Transformations & Data Quality Tests
Open **Terminal 3**:
```bash
cd dbt_project
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..
```

### 6. Launch FastAPI Web Console & Swagger Docs
Open **Terminal 4**:
```bash
python src/main.py
```
Open your browser at:
- **Analyst Web Dashboard**: `http://localhost:8000`
- **Interactive OpenAPI Specs**: `http://localhost:8000/docs`
