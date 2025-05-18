from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

sample_comments = [
    {"text": "I love this new phone!", "location": "USA"},
    {"text": "This is terrible.", "location": "UK"},
    {"text": "So happy with the service.", "location": "India"},
    {"text": "Really bad experience...", "location": "Germany"}
]

while True:
    for comment in sample_comments:
        producer.send('comments', comment)
        print(f"Sent: {comment}")
        time.sleep(2)