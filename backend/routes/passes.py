"""Flask Blueprint for pass prediction and satellite position endpoints."""

from datetime import datetime
from collections import defaultdict

from flask import Blueprint, request, jsonify

from services.pass_predictor import predict_passes, geocode_city, get_ground_track
from database.db import get_all_satellites
from pyorbital.orbital import Orbital

passes_bp = Blueprint("passes", __name__)


def _classify_orbit(alt_km):
    """Classify orbit type by altitude."""
    if alt_km < 2000:
        return "LEO"
    if alt_km < 35000:
        return "MEO"
    if alt_km <= 36000:
        return "GEO"
    return "OTHER"


@passes_bp.route("/passes", methods=["GET"])
def get_city_passes():
    """
    GET /api/passes?city=Chennai&hours=24 — Returns upcoming satellite passes over a city.
    """
    try:
        city = request.args.get("city", "").strip()
        if not city:
            return jsonify({"error": "City parameter is required"}), 400

        hours = request.args.get("hours", "24", type=int)
        if hours < 1 or hours > 168:
            hours = 24

        loc = geocode_city(city)
        lat, lon = loc["lat"], loc["lon"]

        satellites = get_all_satellites()[:300]
        all_passes = []

        for sat in satellites:
            try:
                passes_list = predict_passes(
                    sat["tle_line1"],
                    sat["tle_line2"],
                    lat,
                    lon,
                    altitude_km=0,
                    hours_ahead=hours,
                )
                for p in passes_list:
                    track = get_ground_track(
                        sat["tle_line1"], sat["tle_line2"],
                        p["rise_time"], p["set_time"]
                    )
                    all_passes.append(
                        {
                            "satellite_name": sat["name"],
                            "norad_id": sat["norad_id"],
                            "rise_time": p["rise_time"],
                            "peak_time": p["peak_time"],
                            "set_time": p["set_time"],
                            "max_elevation": p["max_elevation"],
                            "duration_seconds": p["duration_seconds"],
                            "ground_track": track,
                        }
                    )
            except Exception:
                continue

        all_passes.sort(key=lambda x: x["rise_time"])

        return jsonify(
            {
                "city": city,
                "lat": lat,
                "lon": lon,
                "passes": all_passes,
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@passes_bp.route("/passes/top", methods=["GET"])
def get_top_pass_satellites():
    """
    GET /api/passes/top?city=Chennai — Returns top 10 satellites with most passes.
    """
    try:
        city = request.args.get("city", "").strip()
        if not city:
            return jsonify({"error": "City parameter is required"}), 400

        loc = geocode_city(city)
        lat, lon = loc["lat"], loc["lon"]

        satellites = get_all_satellites()[:300]
        pass_counts = defaultdict(int)

        for sat in satellites:
            try:
                passes_list = predict_passes(
                    sat["tle_line1"],
                    sat["tle_line2"],
                    lat,
                    lon,
                    altitude_km=0,
                    hours_ahead=24,
                )
                pass_counts[sat["name"]] += len(passes_list)
            except Exception:
                continue

        top = sorted(pass_counts.items(), key=lambda x: -x[1])[:10]
        top_satellites = [{"name": name, "pass_count": count} for name, count in top]

        return jsonify({"city": city, "top_satellites": top_satellites})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@passes_bp.route("/position", methods=["GET"])
def get_satellite_position():
    """
    GET /api/position?norad_id=25544 — Returns current lat/lon/altitude of a satellite.
    """
    try:
        norad_id = request.args.get("norad_id", "").strip()
        if not norad_id:
            return jsonify({"error": "norad_id parameter is required"}), 400

        satellites = get_all_satellites()
        sat = next((s for s in satellites if s["norad_id"] == norad_id), None)
        if not sat:
            return jsonify({"error": "Satellite not found"}), 404

        orb = Orbital("sat", line1=sat["tle_line1"], line2=sat["tle_line2"])
        now = datetime.utcnow()
        lon, lat, alt = orb.get_lonlatalt(now)

        return jsonify(
            {
                "norad_id": norad_id,
                "name": sat["name"],
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "altitude_km": round(float(alt), 2),
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@passes_bp.route("/stats", methods=["GET"])
def get_city_stats():
    """
    GET /api/stats?city=Chennai — Returns dashboard stats for a city.
    """
    try:
        city = request.args.get("city", "").strip()
        if not city:
            return jsonify({"error": "City parameter is required"}), 400

        loc = geocode_city(city)
        lat, lon = loc["lat"], loc["lon"]

        satellites = get_all_satellites()[:300]
        all_passes = []
        orbit_counts = {"LEO": 0, "MEO": 0, "GEO": 0, "OTHER": 0}

        for sat in satellites:
            try:
                orb = Orbital("sat", line1=sat["tle_line1"], line2=sat["tle_line2"])
                _, _, alt_km = orb.get_lonlatalt(datetime.utcnow())
                orbit_type = _classify_orbit(float(alt_km))

                passes_list = predict_passes(
                    sat["tle_line1"],
                    sat["tle_line2"],
                    lat,
                    lon,
                    altitude_km=0,
                    hours_ahead=24 * 7,
                )
                for p in passes_list:
                    orbit_counts[orbit_type] += 1
                    all_passes.append(
                        {
                            "norad_id": sat["norad_id"],
                            "rise_time": p["rise_time"],
                            "duration_seconds": p["duration_seconds"],
                            "orbit_type": orbit_type,
                        }
                    )
            except Exception:
                continue

        total_passes = len(all_passes)
        durations = [p["duration_seconds"] for p in all_passes]
        avg_duration = sum(durations) / len(durations) if durations else 0
        passes_per_day = total_passes / 7.0 if total_passes else 0

        from datetime import timezone
        passes_by_day = [0] * 7
        today_utc = datetime.now(timezone.utc).date()
        for p in all_passes:
            try:
                dt = datetime.fromisoformat(p["rise_time"].replace("Z", "+00:00"))
                day_offset = (dt.date() - today_utc).days
                if 0 <= day_offset < 7:
                    passes_by_day[day_offset] += 1
            except Exception:
                pass

        return jsonify(
            {
                "total_passes": total_passes,
                "avg_duration_seconds": round(avg_duration, 1),
                "passes_per_day": round(passes_per_day, 1),
                "orbit_type_distribution": orbit_counts,
                "passes_by_day": passes_by_day,
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
