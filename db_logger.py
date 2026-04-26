"""
db_logger.py — All SQLite database operations for the crossing system.
Uses context managers for safe connection handling and parameterised queries throughout.
"""

import sqlite3
import threading
import time
from datetime import datetime

from config import DB_PATH

# Module-level lock so concurrent threads can safely call these functions.
_db_lock = threading.Lock()


# ──────────────────────────────────────────────
# Schema initialisation
# ──────────────────────────────────────────────
def init_db():
    """Create tables if they don't already exist."""
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS button_presses (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp         REAL    NOT NULL,
                datetime_str      TEXT,
                side              TEXT,
                input_type        TEXT,
                hour              INTEGER,
                day_of_week       INTEGER,
                temperature       REAL,
                humidity          REAL,
                pressure          REAL,
                presence_detected INTEGER,
                snapshot_path     TEXT,
                wait_time         REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS phase_log (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                phase                TEXT    NOT NULL,
                start_time           REAL,
                end_time             REAL,
                duration             REAL,
                triggered_by_button  INTEGER
            )
        """)
        conn.commit()
    print("[db_logger] Database initialised.")


# ──────────────────────────────────────────────
# Button press logging
# ──────────────────────────────────────────────
def log_button_press(side, input_type, temperature, humidity, pressure,
                     presence_detected, snapshot_path):
    """
    Record a pedestrian button press event.
    Returns the row id so the caller can later update wait_time.
    """
    now = time.time()
    dt = datetime.fromtimestamp(now)
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO button_presses
                (timestamp, datetime_str, side, input_type,
                 hour, day_of_week,
                 temperature, humidity, pressure,
                 presence_detected, snapshot_path, wait_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (
            now,
            dt.strftime("%Y-%m-%d %H:%M:%S"),
            side,
            input_type,
            dt.hour,
            dt.weekday(),          # 0 = Monday … 6 = Sunday
            temperature,
            humidity,
            pressure,
            1 if presence_detected else 0,
            snapshot_path,
        ))
        conn.commit()
        row_id = cur.lastrowid
    print(f"[db_logger] Logged button press id={row_id} side={side} "
          f"input={input_type} presence={presence_detected}")
    return row_id


def update_wait_time(row_id, wait_time):
    """Fill in the wait_time column once the PEDESTRIAN_CROSS phase starts."""
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE button_presses SET wait_time = ? WHERE id = ?
        """, (wait_time, row_id))
        conn.commit()


# ──────────────────────────────────────────────
# Phase logging
# ──────────────────────────────────────────────
def log_phase(phase, start_time, end_time, triggered_by_button):
    """Record an FSM phase with its duration."""
    duration = end_time - start_time
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO phase_log
                (phase, start_time, end_time, duration, triggered_by_button)
            VALUES (?, ?, ?, ?, ?)
        """, (
            phase,
            start_time,
            end_time,
            duration,
            1 if triggered_by_button else 0,
        ))
        conn.commit()
    print(f"[db_logger] Phase {phase} logged "
          f"(duration={duration:.1f}s, button_triggered={triggered_by_button})")


# ──────────────────────────────────────────────
# Query helpers (used by analytics.py)
# ──────────────────────────────────────────────
def fetch_all_button_presses():
    """Return all rows from button_presses as a list of dicts."""
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM button_presses ORDER BY timestamp")
        return [dict(row) for row in cur.fetchall()]


def fetch_all_phases():
    """Return all rows from phase_log as a list of dicts."""
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM phase_log ORDER BY start_time")
        return [dict(row) for row in cur.fetchall()]
    

def fetch_latest_phase():
    
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT phase FROM phase_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else {"phase": "UNKNOWN"}
