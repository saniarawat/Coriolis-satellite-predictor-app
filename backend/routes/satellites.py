"""Flask Blueprint for satellite data endpoints."""

import os

from flask import Blueprint, jsonify, request

from services.celestrak import fetch_and_store_tles, parse_tle_text
from database.db import get_all_satellites, save_satellites

satellites_bp = Blueprint("satellites", __name__)


@satellites_bp.route("", methods=["GET"])
def list_satellites():
    """
    GET /api/satellites — Returns all satellites in the DB.
    """
    try:
        sats = get_all_satellites()
        return jsonify(
            {
                "count": len(sats),
                "satellites": [
                    {"norad_id": s["norad_id"], "name": s["name"], "fetched_at": s["fetched_at"]}
                    for s in sats
                ],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@satellites_bp.route("/refresh", methods=["POST"])
def refresh_satellites():
    """
    POST /api/satellites/refresh — Fetches TLEs from CelesTrak directly.
    Works from local/residential IPs. On Render, use /upload via GitHub Actions instead.
    """
    try:
        count = fetch_and_store_tles()
        return jsonify({"message": f"Fetched {count} satellites", "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@satellites_bp.route("/upload", methods=["POST"])
def upload_satellites():
    """
    POST /api/satellites/upload — Accepts raw TLE text and stores in DB.

    Called by GitHub Actions every 6 hours. GitHub's IPs can reach CelesTrak
    without being blocked, so this bypasses Render's IP-block issue entirely.

    Secured with a Bearer token (REFRESH_SECRET env var) to prevent public abuse.
    """
    secret = os.environ.get("REFRESH_SECRET", "")
    auth_header = request.headers.get("Authorization", "")

    if not secret:
        return jsonify({"error": "REFRESH_SECRET not configured on server"}), 500
    if auth_header != f"Bearer {secret}":
        return jsonify({"error": "Unauthorized"}), 401

    tle_text = request.get_data(as_text=True)
    if not tle_text or not tle_text.strip():
        return jsonify({"error": "No TLE data provided in request body"}), 400

    try:
        satellites = parse_tle_text(tle_text)
        if not satellites:
            return jsonify({"error": "No valid TLE entries found in provided data"}), 400
        save_satellites(satellites)
        return jsonify({"message": f"Uploaded {len(satellites)} satellites", "count": len(satellites)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
