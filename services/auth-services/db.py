import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection(retries=10, delay=3):
    """Retry loop so the service survives Postgres starting up slower than the app."""
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
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.close()
