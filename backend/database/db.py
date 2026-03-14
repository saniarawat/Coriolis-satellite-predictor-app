"""SQLite database module for satellite and pass data."""

import sqlite3
import os
from config import DATABASE_PATH


def _get_connection():
    """Get a database connection. Uses path relative to backend root."""
    db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(db_dir, DATABASE_PATH)
    return sqlite3.connect(db_path)


def init_db():
    """Create tables if they do not exist."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satellites (
            norad_id TEXT PRIMARY KEY,
            name TEXT,
            tle_line1 TEXT,
            tle_line2 TEXT,
            fetched_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            norad_id TEXT,
            city TEXT,
            rise_time TEXT,
            peak_time TEXT,
            set_time TEXT,
            max_elevation REAL,
            duration_seconds INTEGER
        )
    """)
    conn.commit()
    conn.close()


def save_satellites(satellite_list):
    """
    Insert or replace satellite rows.

    Args:
        satellite_list: List of dicts with keys: norad_id, name, tle_line1, tle_line2, fetched_at
    """
    conn = _get_connection()
    cursor = conn.cursor()
    for s in satellite_list:
        cursor.execute(
            """
            INSERT OR REPLACE INTO satellites (norad_id, name, tle_line1, tle_line2, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                s["norad_id"],
                s["name"],
                s["tle_line1"],
                s["tle_line2"],
                s["fetched_at"],
            ),
        )
    conn.commit()
    conn.close()


def get_all_satellites():
    """
    Return all rows from the satellites table.

    Returns:
        List of dicts with keys: norad_id, name, tle_line1, tle_line2, fetched_at
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT norad_id, name, tle_line1, tle_line2, fetched_at FROM satellites")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_passes(pass_list):
    """
    Insert pass prediction rows.

    Args:
        pass_list: List of dicts with keys: norad_id, city, rise_time, peak_time,
                   set_time, max_elevation, duration_seconds
    """
    conn = _get_connection()
    cursor = conn.cursor()
    for p in pass_list:
        cursor.execute(
            """
            INSERT INTO passes (norad_id, city, rise_time, peak_time, set_time, max_elevation, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["norad_id"],
                p["city"],
                p["rise_time"],
                p["peak_time"],
                p["set_time"],
                p["max_elevation"],
                p["duration_seconds"],
            ),
        )
    conn.commit()
    conn.close()


def get_passes(city):
    """
    Return all passes for a given city.

    Args:
        city: City name string

    Returns:
        List of dicts with pass data
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT norad_id, city, rise_time, peak_time, set_time, max_elevation, duration_seconds FROM passes WHERE city = ? ORDER BY rise_time ASC",
        (city,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
