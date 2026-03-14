"""Service for fetching and parsing TLE data from Celestrak API."""

import requests
from datetime import datetime

from config import CELESTRAK_TLE_URL
from database.db import save_satellites


def fetch_and_store_tles():
    """
    Fetch raw TLE text from Celestrak, parse it, and store in the database.

    Returns:
        int: Number of satellites fetched and stored

    Raises:
        Exception: On network or parsing errors
    """
    try:
        response = requests.get(CELESTRAK_TLE_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch TLE data: {e}") from e

    text = response.text
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    satellites = []
    i = 0
    while i < len(lines) - 2:
        line0 = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if len(line1) >= 7 and len(line2) >= 7:
            norad_id = line1[2:7].strip()
            satellites.append(
                {
                    "name": line0,
                    "tle_line1": line1,
                    "tle_line2": line2,
                    "norad_id": norad_id,
                    "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        i += 3

    save_satellites(satellites)
    return len(satellites)
