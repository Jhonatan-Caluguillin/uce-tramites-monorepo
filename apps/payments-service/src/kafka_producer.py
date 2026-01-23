import json
import os
import time
from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

# Recomendación: UN solo topic para todos los eventos de pagos
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "payments.events")

_producer = None


def _build_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def get_producer():
    """Singleton + reintentos cortos por si Kafka demora."""
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
    """Publica sin romper tu API si Kafka falla (best-effort)."""
    try:
        p = get_producer()
        p.send(KAFKA_TOPIC, event)
        p.flush()
    except Exception as e:
        # Importante: NO tumbar el endpoint por Kafka
        print(f"[payments-service] Kafka publish failed: {e}")


def publish_created(event: dict):
    publish_event(event)


def publish_updated(event: dict):
    publish_event(event)

