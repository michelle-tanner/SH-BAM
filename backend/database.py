"""
database.py
-----------
[SQLite] Initializes the SQLite database and exposes a connection helper.

The database file (feedback.db) is created automatically next to this file
the first time init_db() is called (on FastAPI startup).  No installation or
Docker setup is required — SQLite ships with Python's standard library.

Tables
------
  feedback             – user helpfulness ratings (1-5) and optional comments
  email_subscriptions  – weekly-digest email addresses (unique)
"""

import sqlite3
from pathlib import Path

# [SQLite] Single file on disk — change this path if you ever want to relocate
# the database without touching the rest of the code.
DB_PATH = Path(__file__).parent / "feedback.db"


def get_connection() -> sqlite3.Connection:
    """Return an open SQLite connection with row factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safer for concurrent reads
    return conn


def init_db() -> None:
    """
    [SQLite] Create tables if they don't already exist.
    Called once at application startup via the FastAPI lifespan hook.
    """
    conn = get_connection()
    with conn:
        # --- feedback ---------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                rating     INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment    TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- email_subscriptions ----------------------------------------------
        # UNIQUE on email so duplicate subscribes are silently ignored.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()
