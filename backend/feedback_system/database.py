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
  tags                 – category tags created by the Tagger agent
  feedback_tags        – join table linking feedback rows to their assigned tags
  review_queue         – tags that have crossed the alert threshold
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- tags -------------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_by  TEXT NOT NULL DEFAULT 'agent',
                merged_into INTEGER REFERENCES tags(id),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- feedback_tags ----------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id INTEGER NOT NULL REFERENCES feedback(id),
                tag_id      INTEGER NOT NULL REFERENCES tags(id),
                confidence  REAL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- review_queue -----------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id          INTEGER NOT NULL REFERENCES tags(id),
                tag_name        TEXT NOT NULL,
                frequency       INTEGER NOT NULL,
                sample_comments TEXT,
                is_reviewed     INTEGER NOT NULL DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()
