"""Service for predicting satellite passes and geocoding cities."""

import requests
from datetime import datetime

from pyorbital.orbital import Orbital

from config import DEFAULT_MIN_ELEVATION


def predict_passes(tle_line1, tle_line2, latitude, longitude, altitude_km=0, hours_ahead=24):
    """
    Compute satellite passes over a location using pyorbital.

    Only includes passes where max elevation >= DEFAULT_MIN_ELEVATION degrees.

    Args:
        tle_line1: First TLE line
        tle_line2: Second TLE line
        latitude: Observer latitude in degrees north
        longitude: Observer longitude in degrees east
        altitude_km: Observer altitude above sea level in km (default 0)
        hours_ahead: Number of hours to search for passes (default 24)

    Returns:
        List of dicts with keys: rise_time, peak_time, set_time, max_elevation, duration_seconds
        All times as ISO 8601 UTC strings.
    """
    result = []
    try:
        orb = Orbital("sat", line1=tle_line1, line2=tle_line2)
    except Exception:
        return []

    utc_now = datetime.utcnow()
    try:
        passes = orb.get_next_passes(
            utc_now,
            hours_ahead,
            longitude,
            latitude,
            altitude_km,
            horizon=DEFAULT_MIN_ELEVATION,
        )
    except Exception:
        return []

    for rise_dt, set_dt, peak_dt in passes:
        try:
            az, el = orb.get_observer_look(peak_dt, longitude, latitude, altitude_km)
            max_elevation = float(el)
        except Exception:
            continue

        if max_elevation < DEFAULT_MIN_ELEVATION:
            continue

        duration_seconds = int((set_dt - rise_dt).total_seconds())
        result.append(
            {
                "rise_time": rise_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "peak_time": peak_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "set_time": set_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "max_elevation": round(max_elevation, 1),
                "duration_seconds": duration_seconds,
            }
        )

    return result


def get_ground_track(tle_line1, tle_line2, rise_time_str, set_time_str, num_points=50):
    """
    Compute ground track (lat, lon) points from rise to set time.

    Args:
        tle_line1: First TLE line
        tle_line2: Second TLE line
        rise_time_str: ISO 8601 rise time string
        set_time_str: ISO 8601 set time string
        num_points: Number of points to sample (default 50)

    Returns:
        List of [lat, lon] pairs, or empty list on error.
    """
    try:
        from datetime import datetime, timezone
        orb = Orbital("sat", line1=tle_line1, line2=tle_line2)
        rise = datetime.fromisoformat(rise_time_str.replace("Z", "+00:00"))
        set_time = datetime.fromisoformat(set_time_str.replace("Z", "+00:00"))
        duration = (set_time - rise).total_seconds()
        if duration <= 0:
            return []

        points = []
        for i in range(num_points + 1):
            t = rise.timestamp() + (duration * i / num_points)
            dt = datetime.fromtimestamp(t, tz=timezone.utc)
            lon, lat, _ = orb.get_lonlatalt(dt)
            points.append([float(lat), float(lon)])
        return points
    except Exception:
        return []


def geocode_city(city_name):
    """
    Geocode a city name using OpenStreetMap Nominatim.

    Args:
        city_name: Name of the city to search for

    Returns:
        Dict with keys: lat (float), lon (float), display_name (str)

    Raises:
        ValueError: If city not found
    """
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    headers = {"User-Agent": "SatelliteApp/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise ValueError(f"Geocoding failed: {e}") from e

    if not data:
        raise ValueError("City not found")

    result = data[0]
    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", city_name),
    }
