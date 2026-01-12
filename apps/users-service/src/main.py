import hashlib
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from src.db import get_conn
from src.kafka_producer import publish_event

app = FastAPI(title="users-service", version="1.0.0")

# ---------- DB bootstrap ----------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'STUDENT',
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

@app.on_event("startup")
def startup():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    cur.close()
    conn.close()
    print("[users-service] DB ready")

# ---------- Models ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "STUDENT"   # STUDENT | ADMIN | STAFF (lo que uses)
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: str

# ---------- Helpers ----------
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()

def row_to_user(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "full_name": row[2],
        "role": row[3],
        "created_at": str(row[4]),
    }

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"ok": True, "service": "users-service"}

@app.post("/users", response_model=UserOut)
def create_user(body: UserCreate):
    role = body.role.upper()

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO users (email, full_name, role, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, full_name, role, created_at;
            """,
            (str(body.email), body.full_name, role, hash_password(body.password)),
        )
        row = cur.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        # típico: email duplicado
        raise HTTPException(status_code=400, detail=f"Cannot create user: {e}")

    cur.close()
    conn.close()

    user = row_to_user(row)

    publish_event({
        "type": "USER_CREATED",
        "user": user,
    })

    return user

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, full_name, role, created_at FROM users WHERE id=%s;",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    return row_to_user(row)

@app.get("/users", response_model=List[UserOut])
def list_users(limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit inválido (1..200)")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, full_name, role, created_at FROM users ORDER BY id DESC LIMIT %s;",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [row_to_user(r) for r in rows]

@app.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate):
    fields = []
    values = []

    if body.full_name is not None:
        fields.append("full_name=%s")
        values.append(body.full_name)

    if body.role is not None:
        fields.append("role=%s")
        values.append(body.role.upper())

    if body.password is not None:
        fields.append("password_hash=%s")
        values.append(hash_password(body.password))

    if not fields:
        raise HTTPException(status_code=400, detail="Nada para actualizar")

    values.append(user_id)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE users
        SET {", ".join(fields)}
        WHERE id=%s
        RETURNING id, email, full_name, role, created_at;
        """
        ,
        tuple(values),
    )
    row = cur.fetchone()
    if not row:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Not Found")

    conn.commit()
    cur.close()
    conn.close()

    user = row_to_user(row)

    publish_event({
        "type": "USER_UPDATED",
        "user": user,
    })

    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM users WHERE id=%s RETURNING id;",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Not Found")

    conn.commit()
    cur.close()
    conn.close()

    publish_event({
        "type": "USER_DELETED",
        "user_id": user_id,
    })

    return {"ok": True, "deleted": user_id}
