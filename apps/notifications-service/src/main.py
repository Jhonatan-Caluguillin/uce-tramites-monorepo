import json
import os
import time
import threading
from fastapi import FastAPI
from kafka import KafkaConsumer

app = FastAPI(title="Notifications Service", version="0.1.0")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "tramite.creado,documento.subido")

def kafka_worker():
    topics = [t.strip() for t in KAFKA_TOPICS.split(",") if t.strip()]
    print(f"[notifications-service] Booting consumer... topics={topics} bootstrap={KAFKA_BOOTSTRAP}")

    # Reintentos por si Kafka no está listo aún
    consumer = None
    for i in range(30):
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
               auto_offset_reset="earliest",
                enable_auto_commit=True,
               group_id="notifications-service-v2",
            )
            print("[notifications-service] Connected to Kafka ✅")
            break
        except Exception as e:
            print(f"[notifications-service] Kafka not ready ({i+1}/30): {e}")
            time.sleep(2)

    if consumer is None:
        raise RuntimeError("Kafka not available after retries")

    for msg in consumer:
        try:
            event = msg.value
            print(f"[notifications-service] Event received topic={msg.topic}: {event}")
        except Exception as e:
            print(f"[notifications-service] Error processing message: {e}")

@app.on_event("startup")
def start_consumer():
    t = threading.Thread(target=kafka_worker, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications-service"}
