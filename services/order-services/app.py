import os
import logging
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from db import get_connection, init_db
from mq import publish_order_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s order-service %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

REQUEST_COUNT = Counter("order_requests_total", "Total requests to order-service", ["endpoint", "method", "status"])
REQUEST_LATENCY = Histogram("order_request_latency_seconds", "Request latency", ["endpoint"])
ORDERS_CREATED = Counter("orders_created_total", "Total orders created")

try:
    init_db()
except Exception as e:
    logger.error(f"DB init failed at startup, will retry on first request: {e}")


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="order-service"), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/orders", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/orders").time()
def create_order():
    data = request.get_json(silent=True) or {}
    user_email = data.get("user_email")
    item = data.get("item")
    quantity = data.get("quantity", 1)

    if not user_email or not item:
        REQUEST_COUNT.labels("/orders", "POST", "400").inc()
        return jsonify(error="user_email and item are required"), 400

    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (user_email, item, quantity) VALUES (%s, %s, %s) RETURNING id, status",
            (user_email, item, quantity),
        )
        order = cur.fetchone()
    conn.close()

    event = {"order_id": order["id"], "user_email": user_email, "item": item, "quantity": quantity}
    publish_order_event(event)

    ORDERS_CREATED.inc()
    REQUEST_COUNT.labels("/orders", "POST", "201").inc()
    return jsonify(id=order["id"], status=order["status"]), 201


@app.route("/orders", methods=["GET"])
@REQUEST_LATENCY.labels(endpoint="/orders_list").time()
def list_orders():
    user_email = request.args.get("user_email")
    conn = get_connection()
    with conn, conn.cursor() as cur:
        if user_email:
            cur.execute("SELECT * FROM orders WHERE user_email = %s ORDER BY created_at DESC", (user_email,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100")
        orders = cur.fetchall()
    conn.close()

    REQUEST_COUNT.labels("/orders", "GET", "200").inc()
    return jsonify(orders=orders), 200


@app.route("/orders/<int:order_id>/status", methods=["PATCH"])
def update_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("PENDING", "PROCESSING", "COMPLETED", "FAILED"):
        return jsonify(error="invalid status"), 400

    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute("UPDATE orders SET status = %s WHERE id = %s RETURNING id, status", (new_status, order_id))
        updated = cur.fetchone()
    conn.close()

    if not updated:
        return jsonify(error="order not found"), 404
    return jsonify(id=updated["id"], status=updated["status"]), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("ORDER_SERVICE_PORT", 8002)))
