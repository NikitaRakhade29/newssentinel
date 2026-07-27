import json
import os
import pandas as pd
from confluent_kafka import Consumer, KafkaError
from deltalake import write_deltalake
from dotenv import load_dotenv
from sentiment_analyzer import analyze_sentiment

load_dotenv()

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "live-news")
DELTA_PATH = "./data/bronze_news"

consumer_config = {
    'bootstrap.servers': KAFKA_SERVERS,
    'group.id': 'newssentinel-lakehouse-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_config)
consumer.subscribe([TOPIC])

def process_batch(records):
    if not records:
        return
    
    df = pd.DataFrame(records)
    
    sentiments = df['title'].apply(analyze_sentiment)
    df['sentiment_score'] = [s['compound'] for s in sentiments]
    df['sentiment_label'] = [s['sentiment_label'] for s in sentiments]
    df['ingested_at'] = pd.Timestamp.now().isoformat()
    
    write_deltalake(
        DELTA_PATH,
        df,
        mode='append'
    )
    print(f"Persisted {len(df)} records to Delta Lake at {DELTA_PATH}")

def main():
    print(f"Consumer started. Listening to topic '{TOPIC}'...")
    batch = []
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                if batch:
                    process_batch(batch)
                    batch = []
                continue
                
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Consumer error: {msg.error()}")
                continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
                batch.append(data)
                
                if len(batch) >= 10:
                    process_batch(batch)
                    batch = []
            except Exception as e:
                print(f"Error parsing message: {e}")

    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        if batch:
            process_batch(batch)
        consumer.close()

if __name__ == "__main__":
    main()
