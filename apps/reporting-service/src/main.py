from fastapi import FastAPI, Query
from src.db import get_conn

app = FastAPI(title="reporting-service", version="1.0.0")

@app.get("/health")
def health():
    return {"ok": True, "service": "reporting-service"}

@app.get("/reports/overview")
def overview():
    """
    KPI general:
    - totales: users, students, tramites, documents, payments
    - pagos por estado + total monto
    """
    conn = get_conn()
    cur = conn.cursor()

    # Ajusta nombres de tablas si en tu DB se llaman distinto.
    cur.execute("SELECT COUNT(*) FROM users;")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM students;")
    students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tramites;")
    tramites = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM documents;")
    documents = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM payments;")
    payments = cur.fetchone()[0]

    cur.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN estado='PENDING' THEN 1 ELSE 0 END),0) AS pending,
          COALESCE(SUM(CASE WHEN estado='PAID' THEN 1 ELSE 0 END),0)    AS paid,
          COALESCE(SUM(CASE WHEN estado='FAILED' THEN 1 ELSE 0 END),0)  AS failed,
          COALESCE(SUM(monto),0) AS total_amount
        FROM payments;
    """)
    row = cur.fetchone()
    payments_by_status = {
        "PENDING": int(row[0]),
        "PAID": int(row[1]),
        "FAILED": int(row[2]),
        "TOTAL_AMOUNT": float(row[3]),
    }

    cur.close()
    conn.close()

    return {
        "users": users,
        "students": students,
        "tramites": tramites,
        "documents": documents,
        "payments": payments,
        "payments_by_status": payments_by_status,
    }

@app.get("/reports/payments")
def payments_report(
    from_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    to_date: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    """
    Reporte pagos por rango de fechas (created_at).
    """
    conn = get_conn()
    cur = conn.cursor()

    base = """
        SELECT id, tramite_id, metodo, monto, moneda, estado, created_at
        FROM payments
        WHERE 1=1
    """
    params = []
    if from_date:
        base += " AND created_at >= %s"
        params.append(from_date)
    if to_date:
        base += " AND created_at <= %s"
        params.append(to_date)

    base += " ORDER BY created_at DESC LIMIT 200;"

    cur.execute(base, tuple(params))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "tramite_id": r[1],
            "metodo": r[2],
            "monto": float(r[3]),
            "moneda": r[4],
            "estado": r[5],
            "created_at": str(r[6]),
        })
    return {"count": len(data), "items": data}

@app.get("/reports/tramites")
def tramites_report(estado: str | None = None):
    """
    Reporte simple de trámites por estado.
    """
    conn = get_conn()
    cur = conn.cursor()

    if estado:
        cur.execute("""
            SELECT id, estudiante_id, tipo, estado, created_at
            FROM tramites
            WHERE estado = %s
            ORDER BY created_at DESC
            LIMIT 200;
        """, (estado,))
    else:
        cur.execute("""
            SELECT id, estudiante_id, tipo, estado, created_at
            FROM tramites
            ORDER BY created_at DESC
            LIMIT 200;
        """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    items = [{
        "id": r[0],
        "estudiante_id": r[1],
        "tipo": r[2],
        "estado": r[3],
        "created_at": str(r[4]),
    } for r in rows]

    return {"count": len(items), "items": items}

@app.get("/reports/summary")
def summary():
    """
    Resumen ejecutivo (alias ampliado de overview).
    Útil para el endpoint del paso 1: /reports/summary
    """
    conn = get_conn()
    cur = conn.cursor()

    # Totales
    cur.execute("SELECT COUNT(*) FROM users;")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM students;")
    students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tramites;")
    tramites = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM documents;")
    documents = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM payments;")
    payments = cur.fetchone()[0]

    # Trámites por estado (top)
    cur.execute("""
        SELECT estado, COUNT(*) as total
        FROM tramites
        GROUP BY estado
        ORDER BY total DESC;
    """)
    tramites_by_status = [{"estado": r[0], "total": int(r[1])} for r in cur.fetchall()]

    # Pagos por estado + total monto
    cur.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN estado='PENDING' THEN 1 ELSE 0 END),0) AS pending,
          COALESCE(SUM(CASE WHEN estado='PAID' THEN 1 ELSE 0 END),0)    AS paid,
          COALESCE(SUM(CASE WHEN estado='FAILED' THEN 1 ELSE 0 END),0)  AS failed,
          COALESCE(SUM(monto),0) AS total_amount
        FROM payments;
    """)
    row = cur.fetchone()
    payments_by_status = {
        "PENDING": int(row[0]),
        "PAID": int(row[1]),
        "FAILED": int(row[2]),
        "TOTAL_AMOUNT": float(row[3]),
    }

    cur.close()
    conn.close()

    return {
        "ok": True,
        "service": "reporting-service",
        "totals": {
            "users": users,
            "students": students,
            "tramites": tramites,
            "documents": documents,
            "payments": payments,
        },
        "tramites_by_status": tramites_by_status,
        "payments_by_status": payments_by_status,
    }

