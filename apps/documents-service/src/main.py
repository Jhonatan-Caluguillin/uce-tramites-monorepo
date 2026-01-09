import json
import os
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from kafka import KafkaProducer

app = FastAPI(title="Documents Service", version="0.1.0")

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "documento.subido")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

# DB
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "uce_tramites")
DB_USER = os.getenv("DB_USER", "uce")
DB_PASS = os.getenv("DB_PASS", "uce123")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

class DocumentCreate(BaseModel):
    tramite_id: int
    nombre: str
    url: str

@app.get("/health")
def health():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "service": "documents-service", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "service": "documents-service", "db": "fail", "error": str(e)}


@app.get("/documents/{tramite_id}")
def listar_documentos_por_tramite(tramite_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, tramite_id, nombre, url, estado, created_at
        FROM documents
        WHERE tramite_id = %s
        ORDER BY created_at DESC;
        """,
        (tramite_id,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "tramite_id": r[1],
            "nombre": r[2],
            "url": r[3],
            "estado": r[4],
            "created_at": str(r[5]),
        }
        for r in rows
    ]


@app.post("/documents")
def subir_documento(data: DocumentCreate):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO documents (tramite_id, nombre, url)
        VALUES (%s, %s, %s)
        RETURNING id, tramite_id, nombre, url, estado, created_at;
        """,
        (data.tramite_id, data.nombre, data.url),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    event = {
        "id": row[0],
        "tramite_id": row[1],
        "nombre": row[2],
        "url": row[3],
        "estado": row[4],
        "created_at": str(row[5]),
    }

    producer.send(TOPIC, event)
    producer.flush()

    return event
