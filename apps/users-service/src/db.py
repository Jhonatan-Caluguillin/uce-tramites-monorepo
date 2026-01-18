import os
import psycopg2

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "uce_tramites"),
        user=os.getenv("DB_USER", "uce"),
        password=os.getenv("DB_PASS", "uce123"),
    )
