import json
import time
import os
import requests
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "live-news")

producer_config = {
    'bootstrap.servers': KAFKA_SERVERS
}

producer = Producer(producer_config)

def get_top_story_ids():
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()[:30]
    return []

def get_story_details(story_id):
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()
    return None

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Sent: {msg.key().decode('utf-8') if msg.key() else 'item'}")

def main():
    print("Starting HackerNews Live Producer...")
    seen_ids = set()
    
    while True:
        try:
            story_ids = get_top_story_ids()
            for sid in story_ids:
                if sid in seen_ids:
                    continue
                
                story = get_story_details(sid)
                if story and story.get('type') == 'story' and 'title' in story:
                    payload = {
                        'story_id': str(story.get('id')),
                        'title': story.get('title', ''),
                        'url': story.get('url', ''),
                        'author': story.get('by', 'anonymous'),
                        'score': story.get('score', 0),
                        'comments': story.get('descendants', 0),
                        'created_at': story.get('time', int(time.time()))
                    }
                    
                    producer.produce(
                        TOPIC,
                        key=payload['story_id'],
                        value=json.dumps(payload),
                        callback=delivery_report
                    )
                    producer.poll(0)
                    seen_ids.add(sid)
                    print(f"Produced story: {payload['title']}")
                    time.sleep(1)
            
            producer.flush()
            time.sleep(15)
            
        except Exception as e:
            print(f"Error in producer loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
