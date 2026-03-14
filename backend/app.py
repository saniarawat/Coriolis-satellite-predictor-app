"""Main Flask application for Satellites Over My City backend."""

import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, send_from_directory

from database.db import init_db
from routes.satellites import satellites_bp
from routes.passes import passes_bp

app = Flask(__name__)

# CORS for API (needed when frontend is on different origin during local dev)
if os.environ.get("FLASK_ENV") == "development":
    from flask_cors import CORS
    CORS(app)

init_db()

app.register_blueprint(satellites_bp, url_prefix="/api/satellites")
app.register_blueprint(passes_bp, url_prefix="/api")


@app.route("/api/health", methods=["GET"])
def health():
    """GET /api/health — Health check endpoint."""
    return jsonify(
        {"status": "ok", "message": "Satellite backend is running"}
    )


# Serve frontend (for production deployment)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@app.route("/")
def index():
    """Serve the frontend index.html."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Serve frontend static files (css, js, etc)."""
    if path.startswith("api/"):
        return {"error": "Not found"}, 404
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
