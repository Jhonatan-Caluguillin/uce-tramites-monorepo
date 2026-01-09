import json
import os
import time
import signal
import sys
from datetime import datetime

import psycopg2
from kafka import KafkaConsumer

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tramite.creado")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "workflow-service")

# DB
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "uce_tramites")
DB_USER = os.getenv("DB_USER", "uce")
DB_PASS = os.getenv("DB_PASS", "uce123")

RUNNING = True


def log(msg: str):
    print(f"{datetime.utcnow().isoformat()}Z {msg}", flush=True)


def handle_shutdown(signum, frame):
    global RUNNING
    RUNNING = False
    log("[workflow-service] Shutdown signal received. Exiting...")


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )


def update_status(tramite_id: int, nuevo_estado: str, retries: int = 10, sleep_s: int = 2):
    for i in range(retries):
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE tramites SET estado=%s WHERE id=%s;",
                (nuevo_estado, tramite_id),
            )
            conn.commit()
            cur.close()
            conn.close()
            return
        except Exception as e:
            log(f"[workflow-service] DB not ready ({i+1}/{retries}): {e}")
            time.sleep(sleep_s)

    raise RuntimeError("DB not available after retries")


def main():
    log(f"[workflow-service] Booting... topic={TOPIC} bootstrap={KAFKA_BOOTSTRAP} group_id={GROUP_ID}")

    # Retry Kafka
    consumer = None
    for i in range(30):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id=GROUP_ID,
            )
            log("[workflow-service] Connected to Kafka ✅")
            break
        except Exception as e:
            log(f"[workflow-service] Kafka not ready ({i+1}/30): {e}")
            time.sleep(2)

    if consumer is None:
        raise RuntimeError("Kafka not available after retries")

    # Consume loop
    while RUNNING:
        for msg in consumer:
            if not RUNNING:
                break
            try:
                event = msg.value
                tramite_id = int(event["id"])

                log(f"[workflow-service] Event received: tramite_id={tramite_id} -> EN_PROCESO")
                update_status(tramite_id, "EN_PROCESO")
                log(f"[workflow-service] Updated tramite {tramite_id} ✅")

            except Exception as e:
                log(f"[workflow-service] Error processing message: {e}")

    try:
        consumer.close()
    except Exception:
        pass

    log("[workflow-service] Stopped.")


if __name__ == "__main__":
    main()
