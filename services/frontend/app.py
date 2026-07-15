import os
from flask import Flask, render_template
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "frontend"}, 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("FRONTEND_PORT", 3000)))
