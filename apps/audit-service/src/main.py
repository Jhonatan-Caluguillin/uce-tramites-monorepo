import json
import os
import time
import threading
from datetime import datetime
from fastapi import FastAPI
from kafka import KafkaConsumer
from pymongo import MongoClient

app = FastAPI(title="Audit Service", version="0.1.0")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "tramite.creado,documento.subido")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "uce_audit")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "events")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db[MONGO_COLLECTION]

def kafka_worker():
    topics = [t.strip() for t in KAFKA_TOPICS.split(",") if t.strip()]
    print(f"[audit-service] Booting consumer... topics={topics} bootstrap={KAFKA_BOOTSTRAP}")

    consumer = None
    for i in range(30):
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="audit-service",
            )
            print("[audit-service] Connected to Kafka ✅")
            break
        except Exception as e:
            print(f"[audit-service] Kafka not ready ({i+1}/30): {e}")
            time.sleep(2)

    if consumer is None:
        raise RuntimeError("Kafka not available after retries")

    for msg in consumer:
        try:
            event = msg.value
            doc = {
                "topic": msg.topic,
                "event": event,
                "received_at": datetime.utcnow().isoformat() + "Z",
            }
            col.insert_one(doc)
            print(f"[audit-service] Saved event topic={msg.topic} ✅")
        except Exception as e:
            print(f"[audit-service] Error processing message: {e}")

@app.on_event("startup")
def start_consumer():
    t = threading.Thread(target=kafka_worker, daemon=True)
    t.start()

@app.get("/health")
def health():
    try:
        db.command("ping")
        return {"status": "ok", "service": "audit-service", "mongo": "ok"}
    except Exception as e:
        return {"status": "degraded", "service": "audit-service", "mongo": "fail", "error": str(e)}
