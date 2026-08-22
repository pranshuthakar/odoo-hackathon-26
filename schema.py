"""
schema.py — GlobeTrotter Database Schema
=========================================
Defines the SQLite tables for the travel-planning app.
Run this file directly (`python schema.py`) to create / reset the database,
or import `init_db` from your Flask app to set up tables on first launch.

Tables
------
users       → registered accounts
trips       → a user's travel plans
stops       → cities within a trip (ordered)
activities  → things to do at each stop, with costs
"""

import sqlite3
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The database file lives right next to this script.
# Change the name here if you want a different filename.
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "globetrotter.db")

# ---------------------------------------------------------------------------
# SQL statements  (CREATE TABLE IF NOT EXISTS → safe to run many times)
# ---------------------------------------------------------------------------

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    email    TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL          -- store a HASHED password in production!
);
"""

CREATE_TRIPS = """
CREATE TABLE IF NOT EXISTS trips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,      -- ISO-8601 format: 'YYYY-MM-DD'
    end_date    TEXT    NOT NULL,
    description TEXT    DEFAULT '',

    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""

CREATE_STOPS = """
CREATE TABLE IF NOT EXISTS stops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id     INTEGER NOT NULL,
    city_name   TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,   -- controls the order of cities

    FOREIGN KEY (trip_id) REFERENCES trips (id) ON DELETE CASCADE
);
"""

CREATE_ACTIVITIES = """
CREATE TABLE IF NOT EXISTS activities (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id  INTEGER NOT NULL,
    name     TEXT    NOT NULL,
    cost     REAL    NOT NULL DEFAULT 0.0,     -- monetary cost
    duration TEXT    DEFAULT '',               -- e.g. '2 hours', '30 min'
    category TEXT    DEFAULT 'general',        -- sightseeing, food, adventure…

    FOREIGN KEY (stop_id) REFERENCES stops (id) ON DELETE CASCADE
);
"""

# ---------------------------------------------------------------------------
# Initialiser function
# ---------------------------------------------------------------------------

def init_db(db_path=None):
    """
    Create all tables if they don't already exist.

    Parameters
    ----------
    db_path : str, optional
        Path to the SQLite file.  Defaults to DATABASE (globetrotter.db).

    Returns
    -------
    str
        The absolute path of the database file that was initialised.
    """
    if db_path is None:
        db_path = DATABASE

    conn = sqlite3.connect(db_path)

    # Enable foreign-key enforcement (SQLite has it OFF by default!)
    conn.execute("PRAGMA foreign_keys = ON;")

    cursor = conn.cursor()
    cursor.execute(CREATE_USERS)
    cursor.execute(CREATE_TRIPS)
    cursor.execute(CREATE_STOPS)
    cursor.execute(CREATE_ACTIVITIES)

    conn.commit()
    conn.close()

    print(f"✅ Database ready at: {db_path}")
    return db_path


# ---------------------------------------------------------------------------
# Run directly → create the database
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
