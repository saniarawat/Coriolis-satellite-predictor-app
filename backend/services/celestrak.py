"""Service for fetching and parsing TLE data from Space-Track.org."""

import os
import requests
from datetime import datetime

from database.db import save_satellites

# Space-Track endpoints
SPACE_TRACK_LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
SPACE_TRACK_QUERY_URL = "https://www.space-track.org/basicspacedata/query/class/gp/decay_date/null-val/EPOCH/%3Enow-30/orderby/NORAD_CAT_ID/format/3le/emptyresult/show"


def parse_tle_text(text):
    """
    Parse a raw TLE text block into a list of satellite dicts.

    Validates each TLE triplet (name, line1, line2) strictly:
    - line1 must start with '1 ' and be at least 69 chars
    - line2 must start with '2 ' and be at least 69 chars

    Args:
        text: Raw TLE string (name\\nline1\\nline2 repeated)

    Returns:
        List of dicts with keys: norad_id, name, tle_line1, tle_line2, fetched_at
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    satellites = []
    i = 0
    while i < len(lines) - 2:
        name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
        if (line1.startswith("1 ") and line2.startswith("2 ")
                and len(line1) >= 69 and len(line2) >= 69):
            norad_id = line1[2:7].strip()
            satellites.append({
                "name": name,
                "tle_line1": line1,
                "tle_line2": line2,
                "norad_id": norad_id,
                "fetched_at": now,
            })
        i += 3
    return satellites


def fetch_and_store_tles():
    """
    Fetch the full active TLE catalog from Space-Track.org and store in the DB.
    
    This requires SPACETRACK_USER and SPACETRACK_PASSWORD environment variables.
    Space-Track explicitly allows cloud server IPs, bypassing the CelesTrak blocks.

    Returns:
        int: Number of satellites fetched and stored

    Raises:
        ConnectionError: On network, auth, or HTTP errors
    """
    user = os.environ.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASSWORD")
    
    if not user or not password:
        raise ValueError("SPACETRACK_USER and SPACETRACK_PASSWORD environment variables must be set.")

    with requests.Session() as session:
        # 1. Login to establish session cookies
        login_data = {"identity": user, "password": password}
        try:
            login_resp = session.post(SPACE_TRACK_LOGIN_URL, data=login_data, timeout=30)
            login_resp.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to reach Space-Track login: {e}") from e

        # 2. Fetch the active satellite catalog
        try:
            resp = session.get(SPACE_TRACK_QUERY_URL, timeout=120)
            if resp.status_code == 401:
                raise ConnectionError("Space-Track authentication failed. Check your SPACETRACK_USER and SPACETRACK_PASSWORD.")
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to download TLE data from Space-Track: {e}") from e

        text = resp.text.strip()
        if not text:
            raise ConnectionError("Space-Track returned an empty response.")

    satellites = parse_tle_text(text)
    if not satellites:
        raise ValueError("No valid TLE entries parsed from Space-Track response")

    save_satellites(satellites)
    return len(satellites)
