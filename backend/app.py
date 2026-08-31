"""Main Flask application for Satellites Over My City backend."""

import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, send_from_directory

from database.db import init_db, get_all_satellites
from routes.satellites import satellites_bp
from routes.passes import passes_bp
from services.celestrak import fetch_and_store_tles
import threading
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# CORS for API (needed when frontend is on different origin during local dev)
if os.environ.get("FLASK_ENV") == "development":
    from flask_cors import CORS
    CORS(app)

init_db()

app.register_blueprint(satellites_bp, url_prefix="/api/satellites")
app.register_blueprint(passes_bp, url_prefix="/api")

def background_tle_refresher():
    """Background thread to keep TLE data fresh automatically."""
    while True:
        try:
            sats = get_all_satellites()
            # If DB is empty, or it's been 24 hours, fetch fresh data
            if len(sats) == 0:
                logging.info("Database empty, fetching initial Space-Track data...")
                count = fetch_and_store_tles()
                logging.info(f"Successfully fetched {count} satellites.")
            else:
                logging.info("Refreshing Space-Track TLE data (24-hour cycle)...")
                count = fetch_and_store_tles()
                logging.info(f"Successfully refreshed {count} satellites.")
        except Exception as e:
            logging.error(f"Error fetching TLE data: {e}")
        
        # Wait 24 hours before next refresh
        time.sleep(86400)

# Start the background thread
if os.environ.get("FLASK_ENV") != "development": # Avoid double-running in dev reloader
    refresher_thread = threading.Thread(target=background_tle_refresher, daemon=True)
    refresher_thread.start()


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
