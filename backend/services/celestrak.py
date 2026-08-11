"""Service for fetching and parsing TLE data from CelesTrak."""

import requests
from datetime import datetime

from config import CELESTRAK_TLE_URL
from database.db import save_satellites

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SatellitePredictor/1.0)"}


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
    Fetch the full active TLE catalog from CelesTrak and store in the DB.

    NOTE: CelesTrak blocks cloud hosting IP ranges (Render, AWS, GCP, etc.).
    This function works from local/residential IPs only.
    On Render, TLE data is loaded via the GitHub Actions workflow
    (.github/workflows/tle_refresh.yml) which POSTs to /api/satellites/upload.

    Returns:
        int: Number of satellites fetched and stored

    Raises:
        ConnectionError: On network or HTTP errors
    """
    try:
        response = requests.get(CELESTRAK_TLE_URL, headers=HEADERS, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch TLE data: {e}") from e

    text = response.text.strip()
    if not text or text.startswith("GP data has not"):
        raise ConnectionError("CelesTrak returned empty or rate-limited response")

    satellites = parse_tle_text(text)
    if not satellites:
        raise ValueError("No valid TLE entries parsed from CelesTrak response")

    save_satellites(satellites)
    return len(satellites)
