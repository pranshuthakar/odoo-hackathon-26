from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash

from schema import init_db
from db import (
    create_user,
    get_user_by_email,
    create_trip,
    get_trips_by_user,
    delete_trip,
    add_stop,
    get_stops_by_trip,
    add_activity,
    get_activities_by_stop,
    get_budget_breakdown,
)

app = Flask(__name__)

# Change this before production.
app.secret_key = "globetrotter-dev-secret-key"
# =========================
# FRONTEND PAGE ROUTES
# =========================

@app.get("/")
def home():
    return render_template("base.html")


@app.get("/login", endpoint="login")
def login_page():
    return render_template("login.html")


@app.get("/register", endpoint="register")
def register_page():
    return render_template("register.html")


@app.get("/dashboard", endpoint="dashboard")
def dashboard_page():
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    trips = get_trips_by_user(user_id)

    return render_template(
        "dashboard.html",
        trips=trips
    )

@app.get("/create-trip", endpoint="create_trip")
def create_trip_page():
    return render_template("create_trip.html")


@app.get("/itinerary-builder", endpoint="itinerary_builder")
def itinerary_builder_page():
    return render_template("itinerary_builder.html")


@app.get("/itinerary-view", endpoint="itinerary_view")
def itinerary_view_page():
    return render_template("itinerary_view.html")


@app.get("/my-trips", endpoint="my_trips")
def my_trips_page():
    return render_template("my_trips.html")

# Create database tables when the server starts.
init_db()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "status": "ok"
    })


# ============================================================
# AUTHENTICATION
# ============================================================

@app.post("/api/auth/register")
def register_api():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400

    existing_user = get_user_by_email(email)

    if existing_user:
        return jsonify({
            "success": False,
            "message": "Email already registered."
        }), 409

    password_hash = generate_password_hash(password)

    user = create_user(
        name,
        email,
        password_hash
    )

    # Never send password/password_hash back to frontend.
    user.pop("password", None)

    session["user_id"] = user["id"]

    return jsonify({
        "success": True,
        "message": "Registration successful.",
        "user": user
    }), 201


@app.post("/api/auth/login")
def login_api():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    user = get_user_by_email(email)

    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    if not check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    session["user_id"] = user["id"]

    user.pop("password", None)

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user
    })


@app.post("/api/auth/logout")
def logout_api():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


@app.get("/api/auth/me")
def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Not logged in."
        }), 401

    # We don't have get_user_by_id() in db.py,
    # so use the stored email only when available.
    # For now, return the session user ID.
    return jsonify({
        "success": True,
        "user_id": user_id
    })


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def require_login():
    """Return user_id if logged in, otherwise None."""
    return session.get("user_id")


def get_owned_trip(trip_id, user_id):
    """
    Find a trip belonging to the logged-in user.

    db.py currently provides get_trips_by_user(),
    so we use that instead of writing a second database query.
    """
    trips = get_trips_by_user(user_id)

    for trip in trips:
        if trip["id"] == trip_id:
            return trip

    return None


def stop_belongs_to_trip(stop_id, trip_id):
    """Check whether a stop belongs to a specific trip."""
    stops = get_stops_by_trip(trip_id)

    for stop in stops:
        if stop["id"] == stop_id:
            return True

    return False


# ============================================================
# TRIPS
# ============================================================

@app.post("/api/trips")
def create_new_trip():
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    description = data.get("description", "")

    if not name or not start_date or not end_date:
        return jsonify({
            "success": False,
            "message": "Name, start date and end date are required."
        }), 400

    trip = create_trip(
        user_id,
        name,
        start_date,
        end_date,
        description
    )

    return jsonify({
        "success": True,
        "trip": trip
    }), 201


@app.get("/api/trips")
def list_trips():
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trips = get_trips_by_user(user_id)

    return jsonify({
        "success": True,
        "trips": trips
    })


@app.get("/api/trips/<int:trip_id>")
def get_trip(trip_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trip = get_owned_trip(trip_id, user_id)

    if not trip:
        return jsonify({
            "success": False,
            "message": "Trip not found."
        }), 404

    stops = get_stops_by_trip(trip_id)

    for stop in stops:
        stop["activities"] = get_activities_by_stop(stop["id"])

    trip["stops"] = stops

    return jsonify({
        "success": True,
        "trip": trip
    })


@app.delete("/api/trips/<int:trip_id>")
def remove_trip(trip_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trip = get_owned_trip(trip_id, user_id)

    if not trip:
        return jsonify({
            "success": False,
            "message": "Trip not found."
        }), 404

    deleted = delete_trip(trip_id)

    return jsonify({
        "success": deleted,
        "message": "Trip deleted successfully."
    })


# ============================================================
# STOPS / CITIES
# ============================================================

@app.post("/api/trips/<int:trip_id>/stops")
def create_stop(trip_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trip = get_owned_trip(trip_id, user_id)

    if not trip:
        return jsonify({
            "success": False,
            "message": "Trip not found."
        }), 404

    data = request.get_json(silent=True) or {}

    city_name = data.get("city_name", "").strip()
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    order_index = data.get("order_index", 0)

    if not city_name or not start_date or not end_date:
        return jsonify({
            "success": False,
            "message": "City name, start date and end date are required."
        }), 400

    stop = add_stop(
        trip_id,
        city_name,
        start_date,
        end_date,
        order_index
    )

    return jsonify({
        "success": True,
        "stop": stop
    }), 201


@app.get("/api/trips/<int:trip_id>/stops")
def list_stops(trip_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trip = get_owned_trip(trip_id, user_id)

    if not trip:
        return jsonify({
            "success": False,
            "message": "Trip not found."
        }), 404

    stops = get_stops_by_trip(trip_id)

    return jsonify({
        "success": True,
        "stops": stops
    })


# ============================================================
# ACTIVITIES
# ============================================================

@app.post("/api/stops/<int:stop_id>/activities")
def create_activity(stop_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    data = request.get_json(silent=True) or {}

    # Find the stop through the user's trips.
    owned_stop = None

    trips = get_trips_by_user(user_id)

    for trip in trips:
        stops = get_stops_by_trip(trip["id"])

        for stop in stops:
            if stop["id"] == stop_id:
                owned_stop = stop
                break

        if owned_stop:
            break

    if not owned_stop:
        return jsonify({
            "success": False,
            "message": "Stop not found."
        }), 404

    name = data.get("name", "").strip()
    cost = data.get("cost", 0.0)
    duration = data.get("duration", "")
    category = data.get("category", "general")

    if not name:
        return jsonify({
            "success": False,
            "message": "Activity name is required."
        }), 400

    try:
        cost = float(cost)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Cost must be a number."
        }), 400

    if cost < 0:
        return jsonify({
            "success": False,
            "message": "Cost cannot be negative."
        }), 400

    activity = add_activity(
        stop_id,
        name,
        cost,
        duration,
        category
    )

    return jsonify({
        "success": True,
        "activity": activity
    }), 201


@app.get("/api/stops/<int:stop_id>/activities")
def list_activities(stop_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    # Verify ownership through user's trips.
    owned = False

    for trip in get_trips_by_user(user_id):
        if stop_belongs_to_trip(stop_id, trip["id"]):
            owned = True
            break

    if not owned:
        return jsonify({
            "success": False,
            "message": "Stop not found."
        }), 404

    activities = get_activities_by_stop(stop_id)

    return jsonify({
        "success": True,
        "activities": activities
    })


# ============================================================
# BUDGET
# ============================================================

@app.get("/api/trips/<int:trip_id>/budget")
def trip_budget(trip_id):
    user_id = require_login()

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    trip = get_owned_trip(trip_id, user_id)

    if not trip:
        return jsonify({
            "success": False,
            "message": "Trip not found."
        }), 404

    budget = get_budget_breakdown(trip_id)

    return jsonify({
        "success": True,
        "budget": budget
    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )