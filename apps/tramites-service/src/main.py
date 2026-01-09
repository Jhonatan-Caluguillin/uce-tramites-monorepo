import json
from kafka import KafkaProducer
from fastapi import FastAPI
from pydantic import BaseModel
import os
import psycopg2

app = FastAPI(title="Tramites Service", version="0.1.0")

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

# Postgres
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "uce_tramites")
DB_USER = os.getenv("DB_USER", "uce")
DB_PASS = os.getenv("DB_PASS", "uce123")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

class TramiteCreate(BaseModel):
    estudiante_id: str
    tipo: str

@app.get("/health")
def health():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "service": "tramites-service", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "service": "tramites-service", "db": "fail", "error": str(e)}

@app.post("/tramites")
def crear_tramite(data: TramiteCreate):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO tramites (estudiante_id, tipo)
        VALUES (%s, %s)
        RETURNING id, estudiante_id, tipo, estado, created_at;
        """,
        (data.estudiante_id, data.tipo),
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    event = {
        "id": row[0],
        "estudiante_id": row[1],
        "tipo": row[2],
        "estado": row[3],
        "created_at": str(row[4]),
    }

    # Publicar evento a Kafka
    producer.send("tramite.creado", event)
    producer.flush()

    return event

