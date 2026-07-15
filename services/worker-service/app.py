import os
import logging
from flask import Flask, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from consumer import start_background_consumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker-service %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# The Flask app exists mainly to expose /health and /metrics for the
# monitoring stack; the real work happens in the background consumer thread.
start_background_consumer()


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", service="worker-service"), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("WORKER_SERVICE_PORT", 8004)))
