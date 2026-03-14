"""Main Flask application for Satellites Over My City backend."""

import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from flask_cors import CORS

from database.db import init_db
from routes.satellites import satellites_bp
from routes.passes import passes_bp

app = Flask(__name__)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
