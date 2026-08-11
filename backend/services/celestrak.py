"""Service for fetching and parsing TLE data from Celestrak API."""

import requests
from datetime import datetime

from database.db import save_satellites

# Fetch multiple focused groups instead of the huge GROUP=active file.
# This avoids the timeout and rate-limit issues on Render's free tier IPs.
CELESTRAK_GROUPS = [
    "stations",    # ISS, CSS, crewed stations (~30 sats)
    "visual",      # Brightest/most visible objects (~150 sats)
    "weather",     # Weather satellites (~200 sats)
    "noaa",        # NOAA weather sats
    "goes",        # Geostationary GOES
    "resource",    # Earth resources
    "sarsat",      # Search and rescue
    "dmc",         # Disaster monitoring
    "tdrss",       # Tracking and Data Relay
    "argos",       # ARGOS data collection
    "planet",      # Planet Labs
    "spire",       # Spire Global
    "geo",         # Geostationary (~600 sats)
    "starlink",    # Starlink constellation (~6000 sats)
    "iridium",     # Iridium
    "intelsat",    # Intelsat
    "swarm",       # Swarm Technologies
    "amateur",     # Amateur radio satellites (~200 sats)
    "cubesat",     # CubeSats
    "tle-new",     # Newly launched objects
]

CELESTRAK_BASE = "https://celestrak.org/NORAD/elements/gp.php?FORMAT=tle&GROUP={}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SatellitePredictor/1.0)"}


def _parse_tle_text(text):
    """Parse raw TLE text block into a list of satellite dicts."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    satellites = []
    i = 0
    while i < len(lines) - 2:
        name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
        # Validate TLE lines start with correct identifiers
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
    Fetch TLE data from multiple focused CelesTrak groups and store in DB.
    Uses smaller groups to avoid the timeout caused by the full active catalog
    (~14,000 satellites) on Render's free tier.

    Returns:
        int: Total unique satellites fetched and stored

    Raises:
        Exception: If every group fetch fails
    """
    seen_norad = {}  # deduplicate by norad_id
    failed_groups = []

    for group in CELESTRAK_GROUPS:
        url = CELESTRAK_BASE.format(group)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            text = resp.text.strip()
            # CelesTrak returns a plain-text message if rate-limited
            if not text or text.startswith("GP data has not"):
                continue
            for sat in _parse_tle_text(text):
                seen_norad[sat["norad_id"]] = sat
        except Exception:
            failed_groups.append(group)
            continue

    if not seen_norad and failed_groups:
        raise ConnectionError(
            f"Failed to fetch TLE data from all groups: {', '.join(failed_groups)}"
        )

    all_satellites = list(seen_norad.values())
    if all_satellites:
        save_satellites(all_satellites)

    return len(all_satellites)

