"""Flask Blueprint for satellite data endpoints."""

from flask import Blueprint, jsonify

from services.celestrak import fetch_and_store_tles
from database.db import get_all_satellites

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
    POST /api/satellites/refresh — Fetches TLEs from Celestrak and stores in DB.
    """
    try:
        count = fetch_and_store_tles()
        return jsonify({"message": f"Fetched {count} satellites", "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
