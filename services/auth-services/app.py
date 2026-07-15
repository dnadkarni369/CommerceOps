import os
import jwt
import bcrypt
import datetime
import logging
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from db import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s auth-service %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "changeme")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

REQUEST_COUNT = Counter("auth_requests_total", "Total requests to auth-service", ["endpoint", "method", "status"])
REQUEST_LATENCY = Histogram("auth_request_latency_seconds", "Request latency", ["endpoint"])

try:
    init_db()
except Exception as e:
    logger.error(f"DB init failed at startup, will retry on first request: {e}")


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="auth-service"), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/register", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/register").time()
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        REQUEST_COUNT.labels("/register", "POST", "400").inc()
        return jsonify(error="email and password are required"), 400

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_connection()
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                (email, password_hash),
            )
            user = cur.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"register failed: {e}")
        REQUEST_COUNT.labels("/register", "POST", "409").inc()
        return jsonify(error="user already exists or db error"), 409

    REQUEST_COUNT.labels("/register", "POST", "201").inc()
    return jsonify(id=user["id"], email=user["email"]), 201


@app.route("/login", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/login").time()
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        REQUEST_COUNT.labels("/login", "POST", "400").inc()
        return jsonify(error="email and password are required"), 400

    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    conn.close()

    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        REQUEST_COUNT.labels("/login", "POST", "401").inc()
        return jsonify(error="invalid credentials"), 401

    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "email": user["email"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    REQUEST_COUNT.labels("/login", "POST", "200").inc()
    return jsonify(token=token), 200


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return jsonify(valid=True, payload=payload), 200
    except jwt.PyJWTError as e:
        return jsonify(valid=False, error=str(e)), 401


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("AUTH_SERVICE_PORT", 8001)))
