from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.db import get_conn          # o tu import real
from src.kafka_producer import publish_updated  # o tu import real

app = FastAPI(title="payments-service")


@app.get("/health")
def health():
    return {"ok": True}


class PaymentStatusUpdate(BaseModel):
    estado: str  # PENDING | PAID | FAILED


@app.patch("/payments/{payment_id}/status")
def update_payment_status(payment_id: int, body: PaymentStatusUpdate):
    estado = body.estado.upper()
    if estado not in ["PENDING", "PAID", "FAILED"]:
        raise HTTPException(status_code=400, detail="estado inválido")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE payments
        SET estado = %s
        WHERE id = %s
        RETURNING id, tramite_id, metodo, monto, moneda, estado, created_at;
        """,
        (estado, payment_id),
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Not Found")

    conn.commit()
    cur.close()
    conn.close()

    event = {
        "type": "PAYMENT_UPDATED",
        "payment_id": row[0],
        "tramite_id": row[1],
        "metodo": row[2],
        "monto": float(row[3]),
        "moneda": row[4],
        "estado": row[5],
        "created_at": str(row[6]),
    }
    publish_updated(event)

    return {"ok": True, "payment_id": payment_id, "estado": estado}


