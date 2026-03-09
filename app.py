"""
ACEest Fitness & Gym Management System
Flask REST API - v3.2.4
"""
import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config.setdefault("DATABASE", os.environ.get("DATABASE_URL", "aceest_fitness.db"))

# ---------------------------------------------------------------------------
# Program catalogue (translated from the desktop application)
# ---------------------------------------------------------------------------
PROGRAMS = {
    "Fat Loss (FL) - 3 day": {
        "factor": 22,
        "desc": "3-day full-body fat loss program",
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Wed: EMOM 20 min Assault Bike\n"
            "Fri: Bench Press + 21-15-9 WOD"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2,000 kcal"
        ),
    },
    "Fat Loss (FL) - 5 day": {
        "factor": 24,
        "desc": "5-day split, higher volume fat loss program",
        "workout": (
            "Mon: Back Squat 5x5 + AMRAP\n"
            "Tue: EMOM 20 min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: 10RFT Deadlifts / Box Jumps\n"
            "Fri: 30 min Active Recovery"
        ),
        "diet": (
            "Breakfast: 3 Egg Whites + Oats Idli\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2,000 kcal"
        ),
    },
    "Muscle Gain (MG) - PPL": {
        "factor": 35,
        "desc": "Push/Pull/Legs hypertrophy split",
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "Breakfast: 4 Eggs + Peanut Butter Oats\n"
            "Lunch: Chicken Biryani (250 g Chicken)\n"
            "Dinner: Mutton Curry + Jeera Rice\n"
            "Target: ~3,200 kcal"
        ),
    },
    "Beginner (BG)": {
        "factor": 26,
        "desc": "3-day beginner full-body program — technique mastery",
        "workout": (
            "Circuit Training (3x/week):\n"
            "- Air Squats\n"
            "- Ring Rows\n"
            "- Push-ups\n"
            "Focus: Technique & Form (90% Threshold)"
        ),
        "diet": (
            "Balanced Tamil Meals\n"
            "Idli / Dosa / Rice + Dal / Chapati\n"
            "Protein Target: 120 g/day"
        ),
    },
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Open a new database connection using the app-configured path."""
    db_path = app.config.get("DATABASE", "aceest_fitness.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    UNIQUE NOT NULL,
            age              INTEGER,
            height           REAL,
            weight           REAL,
            program          TEXT,
            calories         INTEGER,
            target_weight    REAL,
            target_adherence INTEGER
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT    NOT NULL,
            week        TEXT    NOT NULL,
            adherence   INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT    NOT NULL,
            date         TEXT    NOT NULL,
            workout_type TEXT,
            duration_min INTEGER,
            notes        TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            weight      REAL,
            waist       REAL,
            bodyfat     REAL
        )
        """
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# BMI helper (pure function — easy to unit-test)
# ---------------------------------------------------------------------------
def compute_bmi(height_cm: float, weight_kg: float) -> dict:
    """Return BMI value, category and risk note for given height/weight."""
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)

    if bmi < 18.5:
        category = "Underweight"
        risk = "Potential nutrient deficiency, low energy."
    elif bmi < 25.0:
        category = "Normal"
        risk = "Low risk if active and strong."
    elif bmi < 30.0:
        category = "Overweight"
        risk = "Moderate risk; focus on adherence and progressive activity."
    else:
        category = "Obese"
        risk = "Higher risk; prioritize fat loss, consistency, and supervision."

    return {"bmi": bmi, "category": category, "risk": risk}


def compute_calories(weight_kg: float, program_name: str) -> int | None:
    """Return estimated daily calories based on program factor."""
    prog = PROGRAMS.get(program_name)
    if prog and weight_kg and weight_kg > 0:
        return int(weight_kg * prog["factor"])
    return None


# ---------------------------------------------------------------------------
# Routes — Home & Programs
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "app": "ACEest Fitness & Gym Management",
            "version": "3.2.4",
            "status": "running",
            "endpoints": [
                "GET  /programs",
                "GET  /clients",
                "POST /clients",
                "GET  /clients/<name>",
                "POST /clients/<name>/progress",
                "POST /clients/<name>/workout",
                "POST /clients/<name>/metrics",
                "GET  /bmi?height=<cm>&weight=<kg>",
            ],
        }
    )


@app.route("/programs", methods=["GET"])
def get_programs():
    """Return all available fitness programs."""
    return jsonify(PROGRAMS)


@app.route("/programs/<name>", methods=["GET"])
def get_program(name):
    """Return a single program by name."""
    prog = PROGRAMS.get(name)
    if not prog:
        return jsonify({"error": "Program not found"}), 404
    return jsonify({name: prog})


# ---------------------------------------------------------------------------
# Routes — Clients
# ---------------------------------------------------------------------------
@app.route("/clients", methods=["GET"])
def get_clients():
    """List all clients (name, program, calories)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, program, calories FROM clients ORDER BY name")
    clients = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(clients)


@app.route("/clients", methods=["POST"])
def create_client():
    """Create or update a client record."""
    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    if data.get("program") and data["program"] not in PROGRAMS:
        return jsonify({"error": f"Unknown program: {data['program']}"}), 400

    name = data["name"].strip()
    weight = data.get("weight")
    program = data.get("program", "")
    calories = compute_calories(weight, program) if weight else None

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO clients
                (name, age, height, weight, program, calories, target_weight, target_adherence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                data.get("age"),
                data.get("height"),
                weight,
                program,
                calories,
                data.get("target_weight"),
                data.get("target_adherence"),
            ),
        )
        conn.commit()
        return jsonify({"message": f"Client '{name}' saved", "calories": calories}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.route("/clients/<name>", methods=["GET"])
def get_client(name):
    """Retrieve a single client record."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients WHERE name=?", (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Client not found"}), 404
    return jsonify(dict(row))


# ---------------------------------------------------------------------------
# Routes — Progress / Workout / Metrics
# ---------------------------------------------------------------------------
@app.route("/clients/<name>/progress", methods=["POST"])
def log_progress(name):
    """Log weekly adherence progress for a client."""
    data = request.get_json(silent=True)
    if not data or "adherence" not in data:
        return jsonify({"error": "adherence value is required"}), 400

    adherence = int(data["adherence"])
    if not (0 <= adherence <= 100):
        return jsonify({"error": "adherence must be between 0 and 100"}), 400

    week = data.get("week") or datetime.now().strftime("Week %U - %Y")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            (name, week, adherence),
        )
        conn.commit()
        return jsonify({"message": "Progress logged", "week": week, "adherence": adherence}), 201
    finally:
        conn.close()


@app.route("/clients/<name>/workout", methods=["POST"])
def log_workout(name):
    """Log a workout session for a client."""
    data = request.get_json(silent=True)
    if not data or not data.get("date") or not data.get("workout_type"):
        return jsonify({"error": "date and workout_type are required"}), 400

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                data["date"],
                data["workout_type"],
                data.get("duration_min", 60),
                data.get("notes", ""),
            ),
        )
        conn.commit()
        return jsonify({"message": "Workout logged"}), 201
    finally:
        conn.close()


@app.route("/clients/<name>/metrics", methods=["POST"])
def log_metrics(name):
    """Log body metrics (weight, waist, bodyfat) for a client."""
    data = request.get_json(silent=True)
    if not data or not data.get("date"):
        return jsonify({"error": "date is required"}), 400

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                data["date"],
                data.get("weight"),
                data.get("waist"),
                data.get("bodyfat"),
            ),
        )
        conn.commit()
        return jsonify({"message": "Metrics logged"}), 201
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes — BMI Calculator
# ---------------------------------------------------------------------------
@app.route("/bmi", methods=["GET"])
def bmi_calculator():
    """Calculate BMI. Query params: height (cm), weight (kg)."""
    height = request.args.get("height", type=float)
    weight = request.args.get("weight", type=float)

    if not height or not weight or height <= 0 or weight <= 0:
        return jsonify({"error": "Valid height (cm) and weight (kg) query params required"}), 400

    return jsonify(compute_bmi(height, weight))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
