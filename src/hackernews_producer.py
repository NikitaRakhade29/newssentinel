import json
import time
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "live-news")

producer_config = {
    'bootstrap.servers': KAFKA_SERVERS,
    'client.id': 'hackernews-producer'
}

producer = Producer(producer_config)

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Produced event to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

def fetch_single_story(story_id):
    try:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            story = resp.json()
            if story and story.get('type') == 'story' and 'title' in story:
                return {
                    'story_id': str(story.get('id')),
                    'title': story.get('title'),
                    'url': story.get('url', ''),
                    'author': story.get('by', 'anonymous'),
                    'score': story.get('score', 0),
                    'comments': story.get('descendants', 0),
                    'created_at': story.get('time', int(time.time()))
                }
    except Exception:
        pass
    return None

def fetch_and_produce():
    try:
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        r = requests.get(top_url, timeout=5)
        if r.status_code != 200:
            return
            
        story_ids = r.json()[:50]
        
        # Parallel multi-threaded fetch for high-speed streaming
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_single_story, story_ids))
            
        for story in results:
            if story:
                producer.produce(
                    TOPIC,
                    key=story['story_id'],
                    value=json.dumps(story),
                    callback=delivery_report
                )
        producer.flush()
        print(f"⚡ Batch of {len([s for s in results if s])} live stories streamed to Kafka topic '{TOPIC}'")

    except Exception as e:
        print(f"Producer error: {e}")

def main():
    print(f"High-Speed Live HackerNews Producer started. Streaming to Kafka '{TOPIC}'...")
    while True:
        fetch_and_produce()
        time.sleep(3)

if __name__ == "__main__":
    main()
