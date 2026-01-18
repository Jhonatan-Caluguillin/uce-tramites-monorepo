from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from src.db import get_conn
from src.kafka_producer import publish_created, publish_updated

app = FastAPI(title="students-service", version="1.0.0")


# ---------- DB bootstrap ----------
def ensure_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            cedula VARCHAR(20) UNIQUE NOT NULL,
            full_name VARCHAR(120) NOT NULL,
            email VARCHAR(120),
            carrera VARCHAR(120),
            estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def on_startup():
    ensure_table()


# ---------- Schemas ----------
class StudentCreate(BaseModel):
    cedula: str = Field(..., min_length=6, max_length=20)
    full_name: str = Field(..., min_length=3, max_length=120)
    email: Optional[str] = None
    carrera: Optional[str] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=3, max_length=120)
    email: Optional[str] = None
    carrera: Optional[str] = None
    estado: Optional[str] = None  # ACTIVO | INACTIVO


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"ok": True, "service": "students-service"}


@app.post("/students")
def create_student(body: StudentCreate):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO students (cedula, full_name, email, carrera)
            VALUES (%s, %s, %s, %s)
            RETURNING id, cedula, full_name, email, carrera, estado, created_at;
            """,
            (body.cedula, body.full_name, body.email, body.carrera),
        )
        row = cur.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    cur.close()
    conn.close()

    event = {
        "type": "STUDENT_CREATED",
        "student_id": row["id"],
        "cedula": row["cedula"],
        "full_name": row["full_name"],
        "email": row["email"],
        "carrera": row["carrera"],
        "estado": row["estado"],
        "created_at": str(row["created_at"]),
    }
    publish_created(event)

    return {"ok": True, "student": row}


@app.get("/students/{student_id}")
def get_student(student_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE id=%s;", (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"ok": True, "student": row}


@app.patch("/students/{student_id}")
def update_student(student_id: int, body: StudentUpdate):
    fields = []
    values = []

    if body.full_name is not None:
        fields.append("full_name=%s"); values.append(body.full_name)
    if body.email is not None:
        fields.append("email=%s"); values.append(body.email)
    if body.carrera is not None:
        fields.append("carrera=%s"); values.append(body.carrera)
    if body.estado is not None:
        estado = body.estado.upper()
        if estado not in ["ACTIVO", "INACTIVO"]:
            raise HTTPException(status_code=400, detail="estado inválido")
        fields.append("estado=%s"); values.append(estado)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(student_id)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE students
        SET {", ".join(fields)}
        WHERE id=%s
        RETURNING id, cedula, full_name, email, carrera, estado, created_at;
        """,
        tuple(values),
    )
    row = cur.fetchone()
    if not row:
        conn.rollback()
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Not Found")

    conn.commit()
    cur.close()
    conn.close()

    event = {
        "type": "STUDENT_UPDATED",
        "student_id": row["id"],
        "cedula": row["cedula"],
        "full_name": row["full_name"],
        "email": row["email"],
        "carrera": row["carrera"],
        "estado": row["estado"],
        "updated_at": str(datetime.utcnow()),
    }
    publish_updated(event)

    return {"ok": True, "student": row}


@app.get("/students")
def list_students(limit: int = 50):
    limit = max(1, min(limit, 200))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY id DESC LIMIT %s;", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"ok": True, "items": rows}
