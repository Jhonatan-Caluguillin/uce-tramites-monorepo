import json
import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer

app = FastAPI(title="Payments Service", version="0.1.0")

# Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "pago.realizado")

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

def ensure_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            tramite_id INT NOT NULL,
            metodo VARCHAR(50) NOT NULL,
            monto NUMERIC(10,2) NOT NULL,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            estado VARCHAR(20) NOT NULL DEFAULT 'PAGADO',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

class PaymentCreate(BaseModel):
    tramite_id: int
    metodo: str
    monto: float
    moneda: str = "USD"

@app.on_event("startup")
def startup():
    ensure_table()

@app.get("/health")
def health():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "service": "payments-service", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "service": "payments-service", "db": "fail", "error": str(e)}

@app.post("/payments")
def create_payment(data: PaymentCreate):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO payments (tramite_id, metodo, monto, moneda)
        VALUES (%s, %s, %s, %s)
        RETURNING id, tramite_id, metodo, monto, moneda, estado, created_at;
        """,
        (data.tramite_id, data.metodo, data.monto, data.moneda),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    event = {
        "id": row[0],
        "tramite_id": row[1],
        "metodo": row[2],
        "monto": float(row[3]),
        "moneda": row[4],
        "estado": row[5],
        "created_at": str(row[6]),
    }

    producer.send(KAFKA_TOPIC, event)
    producer.flush()

    return event

@app.get("/payments/{payment_id}")
def get_payment(payment_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, tramite_id, metodo, monto, moneda, estado, created_at FROM payments WHERE id=%s;",
        (payment_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    return {
        "id": row[0],
        "tramite_id": row[1],
        "metodo": row[2],
        "monto": float(row[3]),
        "moneda": row[4],
        "estado": row[5],
        "created_at": str(row[6]),
    }
