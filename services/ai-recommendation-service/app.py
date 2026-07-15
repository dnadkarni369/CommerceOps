import os
import json
import logging
import redis
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s ai-recommendation-service %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

REQUEST_COUNT = Counter("ai_requests_total", "Total requests to ai-recommendation-service", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("ai_request_latency_seconds", "Request latency", ["endpoint"])
CACHE_HITS = Counter("ai_cache_hits_total", "Recommendation cache hits")
CACHE_MISSES = Counter("ai_cache_misses_total", "Recommendation cache misses")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)

# Tiny static catalog used to produce believable "recommendations" without
# needing a real ML model or training data - the point of this service is to
# demonstrate the microservice + caching pattern, not to build a recommender.
CATALOG = {
    "laptop": ["laptop-sleeve", "wireless-mouse", "usb-c-hub"],
    "phone": ["phone-case", "screen-protector", "wireless-charger"],
    "headphones": ["headphone-stand", "aux-cable", "carrying-case"],
    "camera": ["tripod", "memory-card", "camera-bag"],
}
DEFAULT_RECS = ["gift-card", "extended-warranty"]


@app.route("/health", methods=["GET"])
def health():
    try:
        redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return jsonify(status="ok", service="ai-recommendation-service", redis=redis_ok), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/recommend", methods=["GET"])
@REQUEST_LATENCY.labels(endpoint="/recommend").time()
def recommend():
    item = (request.args.get("item") or "").lower().strip()
    if not item:
        REQUEST_COUNT.labels("/recommend", "400").inc()
        return jsonify(error="item query param is required"), 400

    cache_key = f"rec:{item}"
    cached = redis_client.get(cache_key)
    if cached:
        CACHE_HITS.inc()
        REQUEST_COUNT.labels("/recommend", "200").inc()
        return jsonify(item=item, recommendations=json.loads(cached), cached=True), 200

    CACHE_MISSES.inc()
    recs = CATALOG.get(item, DEFAULT_RECS)
    redis_client.setex(cache_key, 300, json.dumps(recs))  # cache for 5 minutes

    REQUEST_COUNT.labels("/recommend", "200").inc()
    return jsonify(item=item, recommendations=recs, cached=False), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("AI_SERVICE_PORT", 8003)))
