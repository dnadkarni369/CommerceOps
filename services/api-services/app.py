import os
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s api-service %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Allows the frontend to call this gateway directly (e.g. http://localhost:8000)
# when it's opened on its own port (3000) instead of through the nginx proxy
# (8080), where paths are same-origin and CORS isn't needed at all. Restrict
# origins to a real domain list before using this in production.
CORS(app, resources={r"/api/*": {"origins": "*"}})

AUTH_SERVICE_URL = f"http://auth-service:{os.getenv('AUTH_SERVICE_PORT', 8001)}"
ORDER_SERVICE_URL = f"http://order-service:{os.getenv('ORDER_SERVICE_PORT', 8002)}"
AI_SERVICE_URL = f"http://ai-recommendation-service:{os.getenv('AI_SERVICE_PORT', 8003)}"

REQUEST_COUNT = Counter("api_requests_total", "Total requests to api-service (gateway)", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Request latency", ["endpoint"])
UPSTREAM_ERRORS = Counter("api_upstream_errors_total", "Errors talking to upstream services", ["upstream"])

TIMEOUT = 5  # seconds - fail fast rather than hang the gateway on a slow downstream


def forward(method, url, **kwargs):
    # Pass the caller's JWT through to whichever service is being proxied to,
    # so downstream services can identify the user without a second login.
    headers = kwargs.pop("headers", {}) or {}
    if "Authorization" in request.headers:
        headers["Authorization"] = request.headers["Authorization"]

    try:
        resp = requests.request(method, url, timeout=TIMEOUT, headers=headers, **kwargs)
        return resp.json(), resp.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"upstream call failed: {url} - {e}")
        return {"error": "upstream service unavailable"}, 502


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="api-service"), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ---- Auth passthrough ----
@app.route("/api/auth/register", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/api/auth/register").time()
def auth_register():
    body, status = forward("POST", f"{AUTH_SERVICE_URL}/register", json=request.get_json(silent=True))
    if status >= 500:
        UPSTREAM_ERRORS.labels("auth-service").inc()
    REQUEST_COUNT.labels("/api/auth/register", str(status)).inc()
    return jsonify(body), status


@app.route("/api/auth/login", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/api/auth/login").time()
def auth_login():
    body, status = forward("POST", f"{AUTH_SERVICE_URL}/login", json=request.get_json(silent=True))
    if status >= 500:
        UPSTREAM_ERRORS.labels("auth-service").inc()
    REQUEST_COUNT.labels("/api/auth/login", str(status)).inc()
    return jsonify(body), status


# ---- Order passthrough ----
@app.route("/api/orders", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/api/orders_create").time()
def orders_create():
    body, status = forward("POST", f"{ORDER_SERVICE_URL}/orders", json=request.get_json(silent=True))
    if status >= 500:
        UPSTREAM_ERRORS.labels("order-service").inc()
    REQUEST_COUNT.labels("/api/orders", str(status)).inc()
    return jsonify(body), status


@app.route("/api/orders", methods=["GET"])
@REQUEST_LATENCY.labels(endpoint="/api/orders_list").time()
def orders_list():
    body, status = forward("GET", f"{ORDER_SERVICE_URL}/orders", params=request.args)
    if status >= 500:
        UPSTREAM_ERRORS.labels("order-service").inc()
    REQUEST_COUNT.labels("/api/orders_list", str(status)).inc()
    return jsonify(body), status


@app.route("/api/orders/<int:order_id>/status", methods=["PATCH"])
@REQUEST_LATENCY.labels(endpoint="/api/orders_update_status").time()
def orders_update_status(order_id):
    body, status = forward(
        "PATCH", f"{ORDER_SERVICE_URL}/orders/{order_id}/status", json=request.get_json(silent=True)
    )
    if status >= 500:
        UPSTREAM_ERRORS.labels("order-service").inc()
    REQUEST_COUNT.labels("/api/orders_update_status", str(status)).inc()
    return jsonify(body), status


# ---- Recommendation passthrough ----
@app.route("/api/recommend", methods=["GET"])
@REQUEST_LATENCY.labels(endpoint="/api/recommend").time()
def recommend():
    body, status = forward("GET", f"{AI_SERVICE_URL}/recommend", params=request.args)
    if status >= 500:
        UPSTREAM_ERRORS.labels("ai-recommendation-service").inc()
    REQUEST_COUNT.labels("/api/recommend", str(status)).inc()
    return jsonify(body), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("API_SERVICE_PORT", 8000)))
