import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection(retries=10, delay=3):
    last_err = None
    for _ in range(retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                user=os.getenv("POSTGRES_USER", "commerceops"),
                password=os.getenv("POSTGRES_PASSWORD", "commerceops"),
                dbname=os.getenv("POSTGRES_DB", "commerceops"),
                cursor_factory=RealDictCursor,
            )
            return conn
        except psycopg2.OperationalError as e:
            last_err = e
            time.sleep(delay)
    raise last_err

def init_db():
    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                item VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.close()
