import os
import logging
from flask import Flask, render_template, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        try:
            return render_template("index.html")
        except Exception:
            logger.exception("Failed to render index page")
            return jsonify({"error": "internal server error"}), 500

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "frontend"}), 200

    @app.route("/metrics", methods=["GET"])
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FRONTEND_PORT", 3000))
    app.run(host="0.0.0.0", port=port)
