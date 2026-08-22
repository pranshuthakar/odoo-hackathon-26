"""
db.py — GlobeTrotter Database Helpers
======================================
Plain, beginner-friendly functions that talk to SQLite.
Import any of them into your Flask routes:

    from db import create_user, get_trips_by_user, get_budget_breakdown

Every function:
  • uses parameterised queries (no SQL-injection risk)
  • returns dicts / lists-of-dicts (easy for Jinja templates & jsonify)
  • opens and closes its own connection (simple, no global state)
"""

import sqlite3
from schema import DATABASE, init_db

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_connection():
    """
    Open a new connection to the database.
    - row_factory = sqlite3.Row  →  rows behave like dicts
    - PRAGMA foreign_keys = ON   →  cascading deletes actually work
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row          # lets us do  row["column_name"]
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain Python dict."""
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════════════

def create_user(name, email, password):
    """
    Register a new user.

    Parameters
    ----------
    name     : str – display name
    email    : str – must be unique
    password : str – ⚠️  hash this before passing in production!

    Returns
    -------
    dict – the newly-created user row  (id, name, email, password)
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?);",
            (name, email, password),
        )
        conn.commit()
        user_id = cursor.lastrowid

        # Fetch the full row to return as a dict
        row = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_user_by_email(email):
    """
    Look up a user by their email address.

    Returns
    -------
    dict or None
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?;", (email,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# TRIPS
# ═══════════════════════════════════════════════════════════════════════════

def create_trip(user_id, name, start_date, end_date, description=""):
    """
    Create a new trip for a user.

    Dates should be ISO-8601 strings ('YYYY-MM-DD').

    Returns
    -------
    dict – the newly-created trip row
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO trips (user_id, name, start_date, end_date, description)
               VALUES (?, ?, ?, ?, ?);""",
            (user_id, name, start_date, end_date, description),
        )
        conn.commit()
        trip_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM trips WHERE id = ?;", (trip_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_trips_by_user(user_id):
    """
    Get every trip belonging to a user, newest first.

    Returns
    -------
    list[dict]
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM trips WHERE user_id = ? ORDER BY start_date DESC;",
            (user_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def delete_trip(trip_id):
    """
    Delete a trip AND all its stops / activities (via ON DELETE CASCADE).

    Returns
    -------
    bool – True if a row was actually deleted, False if trip_id didn't exist
    """
    conn = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM trips WHERE id = ?;", (trip_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# STOPS  (cities within a trip)
# ═══════════════════════════════════════════════════════════════════════════

def add_stop(trip_id, city_name, start_date, end_date, order_index=0):
    """
    Add a city stop to a trip.

    Parameters
    ----------
    order_index : int – position of this stop in the itinerary (0-based)

    Returns
    -------
    dict – the newly-created stop row
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO stops (trip_id, city_name, start_date, end_date, order_index)
               VALUES (?, ?, ?, ?, ?);""",
            (trip_id, city_name, start_date, end_date, order_index),
        )
        conn.commit()
        stop_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM stops WHERE id = ?;", (stop_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_stops_by_trip(trip_id):
    """
    Get all stops for a trip, sorted by order_index.

    Returns
    -------
    list[dict]
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM stops WHERE trip_id = ? ORDER BY order_index ASC;",
            (trip_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVITIES  (things to do at a stop)
# ═══════════════════════════════════════════════════════════════════════════

def add_activity(stop_id, name, cost=0.0, duration="", category="general"):
    """
    Add an activity to a stop.

    Parameters
    ----------
    cost     : float – monetary cost (e.g. 25.50)
    duration : str   – human-readable duration ('2 hours', '45 min')
    category : str   – e.g. 'sightseeing', 'food', 'adventure', 'transport'

    Returns
    -------
    dict – the newly-created activity row
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO activities (stop_id, name, cost, duration, category)
               VALUES (?, ?, ?, ?, ?);""",
            (stop_id, name, cost, duration, category),
        )
        conn.commit()
        activity_id = cursor.lastrowid

        row = conn.execute(
            "SELECT * FROM activities WHERE id = ?;", (activity_id,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_activities_by_stop(stop_id):
    """
    Get all activities for a stop.

    Returns
    -------
    list[dict]
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM activities WHERE stop_id = ? ORDER BY id ASC;",
            (stop_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# BUDGET BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════

def get_budget_breakdown(trip_id):
    """
    Calculate the full budget for a trip.

    Returns
    -------
    dict with two keys:
        "total_cost"   : float  – grand total across every activity
        "by_category"  : list[dict]  – each dict has 'category' and 'cost'

    Example return value:
        {
            "total_cost": 450.00,
            "by_category": [
                {"category": "food",        "cost": 120.00},
                {"category": "sightseeing", "cost": 200.00},
                {"category": "adventure",   "cost": 130.00}
            ]
        }
    """
    conn = _get_connection()
    try:
        # --- total cost across every activity in the trip ---
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(a.cost), 0) AS total_cost
            FROM activities a
            JOIN stops s ON a.stop_id = s.id
            WHERE s.trip_id = ?;
            """,
            (trip_id,),
        ).fetchone()

        total_cost = total_row["total_cost"]

        # --- cost grouped by category ---
        category_rows = conn.execute(
            """
            SELECT a.category, SUM(a.cost) AS cost
            FROM activities a
            JOIN stops s ON a.stop_id = s.id
            WHERE s.trip_id = ?
            GROUP BY a.category
            ORDER BY cost DESC;
            """,
            (trip_id,),
        ).fetchall()

        by_category = _rows_to_dicts(category_rows)

        return {
            "total_cost": round(total_cost, 2),
            "by_category": by_category,
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# SAFE INITIALISATION SCRIPT
# ═══════════════════════════════════════════════════════════════════════════
# Running  `python db.py`  creates the database (if needed) and inserts
# a small set of demo data so you can test immediately.

if __name__ == "__main__":
    # 1. Create the tables (safe to run repeatedly)
    init_db()

    # 2. Insert demo data only if the DB is empty
    conn = _get_connection()
    existing = conn.execute("SELECT COUNT(*) AS n FROM users;").fetchone()["n"]
    conn.close()

    if existing == 0:
        print("\n📦 Inserting demo data …")

        # Create a demo user
        user = create_user("Alice", "alice@example.com", "hashed_pw_123")
        print(f"   User created: {user}")

        # Create a trip
        trip = create_trip(
            user["id"],
            "Euro Adventure 2026",
            "2026-09-01",
            "2026-09-15",
            "Two weeks across Europe!",
        )
        print(f"   Trip created: {trip}")

        # Add stops
        paris = add_stop(trip["id"], "Paris",     "2026-09-01", "2026-09-05", 0)
        rome  = add_stop(trip["id"], "Rome",      "2026-09-05", "2026-09-10", 1)
        berlin = add_stop(trip["id"], "Berlin",   "2026-09-10", "2026-09-15", 2)
        print(f"   Stops: {paris['city_name']}, {rome['city_name']}, {berlin['city_name']}")

        # Add activities
        add_activity(paris["id"], "Eiffel Tower visit",   25.00, "2 hours",  "sightseeing")
        add_activity(paris["id"], "Croissant breakfast",   8.50, "30 min",   "food")
        add_activity(rome["id"],  "Colosseum tour",       16.00, "3 hours",  "sightseeing")
        add_activity(rome["id"],  "Pasta dinner",         22.00, "1 hour",   "food")
        add_activity(rome["id"],  "Vespa rental",         45.00, "4 hours",  "adventure")
        add_activity(berlin["id"], "Berlin Wall memorial",  0.00, "1.5 hours","sightseeing")
        add_activity(berlin["id"], "Street food tour",    15.00, "2 hours",  "food")
        print("   Activities added ✓")

        # Show budget
        budget = get_budget_breakdown(trip["id"])
        print(f"\n💰 Budget Breakdown:")
        print(f"   Total: ${budget['total_cost']}")
        for cat in budget["by_category"]:
            print(f"   • {cat['category']}: ${cat['cost']}")
    else:
        print("ℹ️  Demo data already exists — skipping insert.")

    print("\n🚀 All done! Import from db.py in your Flask app.")
