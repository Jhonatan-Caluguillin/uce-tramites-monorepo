import json
import os
import time
from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "students.events")

_producer = None

def _build_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

def get_producer():
    global _producer
    if _producer is not None:
        return _producer

    last_err = None
    for _ in range(15):
        try:
            _producer = _build_producer()
            return _producer
        except Exception as e:
            last_err = e
            time.sleep(1)

    raise RuntimeError(f"Kafka not available: {last_err}")

def publish_event(event: dict):
    try:
        p = get_producer()
        p.send(KAFKA_TOPIC, event)
        p.flush()
    except Exception as e:
        print(f"[students-service] Kafka publish failed: {e}")

def publish_created(event: dict):
    publish_event(event)

def publish_updated(event: dict):
    publish_event(event)
