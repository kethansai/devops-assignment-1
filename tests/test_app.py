"""
Pytest test suite for ACEest Fitness & Gym Management Flask API.
All tests use an isolated temporary SQLite database so the production
database is never touched.
"""
import json
import os
import tempfile

import pytest

from app import app, init_db, PROGRAMS, compute_bmi, compute_calories


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """Provide a Flask test client backed by a fresh temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    app.config["DATABASE"] = db_path

    with app.test_client() as test_client:
        init_db()
        yield test_client

    os.close(db_fd)
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _json(response):
    return json.loads(response.data)


def _post_client(client, name="Test Athlete", weight=80.0, program="Beginner (BG)"):
    return client.post(
        "/clients",
        json={"name": name, "weight": weight, "program": program, "age": 25, "height": 175.0},
    )


# ---------------------------------------------------------------------------
# Home & Programs
# ---------------------------------------------------------------------------
class TestHome:
    def test_home_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_home_app_name(self, client):
        data = _json(client.get("/"))
        assert data["app"] == "ACEest Fitness & Gym Management"

    def test_home_status_running(self, client):
        data = _json(client.get("/"))
        assert data["status"] == "running"

    def test_home_lists_endpoints(self, client):
        data = _json(client.get("/"))
        assert isinstance(data["endpoints"], list)
        assert len(data["endpoints"]) > 0


class TestPrograms:
    def test_get_programs_returns_200(self, client):
        r = client.get("/programs")
        assert r.status_code == 200

    def test_all_four_programs_present(self, client):
        data = _json(client.get("/programs"))
        assert "Beginner (BG)" in data
        assert "Muscle Gain (MG) - PPL" in data
        assert "Fat Loss (FL) - 3 day" in data
        assert "Fat Loss (FL) - 5 day" in data

    def test_programs_have_required_fields(self, client):
        data = _json(client.get("/programs"))
        for prog_name, prog_data in data.items():
            assert "factor" in prog_data, f"Missing 'factor' in {prog_name}"
            assert "desc" in prog_data, f"Missing 'desc' in {prog_name}"
            assert "workout" in prog_data, f"Missing 'workout' in {prog_name}"
            assert "diet" in prog_data, f"Missing 'diet' in {prog_name}"

    def test_get_single_program(self, client):
        r = client.get("/programs/Beginner (BG)")
        assert r.status_code == 200

    def test_get_unknown_program_returns_404(self, client):
        r = client.get("/programs/NonExistent Program")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Client CRUD
# ---------------------------------------------------------------------------
class TestClients:
    def test_get_clients_empty_list(self, client):
        r = client.get("/clients")
        assert r.status_code == 200
        assert _json(r) == []

    def test_create_client_success(self, client):
        r = _post_client(client)
        assert r.status_code == 201
        data = _json(r)
        assert "Test Athlete" in data["message"]

    def test_create_client_missing_name_returns_400(self, client):
        r = client.post("/clients", json={"weight": 80})
        assert r.status_code == 400

    def test_create_client_unknown_program_returns_400(self, client):
        r = client.post("/clients", json={"name": "X", "program": "Invalid Program"})
        assert r.status_code == 400

    def test_create_client_calorie_calculation(self, client):
        # Beginner factor=26, weight=80 → 80*26 = 2080
        r = client.post("/clients", json={"name": "Calorie Check", "weight": 80, "program": "Beginner (BG)"})
        assert _json(r)["calories"] == 2080

    def test_get_client_after_create(self, client):
        _post_client(client)
        r = client.get("/clients/Test Athlete")
        assert r.status_code == 200
        assert _json(r)["name"] == "Test Athlete"

    def test_get_nonexistent_client_returns_404(self, client):
        r = client.get("/clients/Nobody Here")
        assert r.status_code == 404

    def test_client_list_populated_after_create(self, client):
        _post_client(client, name="Alice")
        _post_client(client, name="Bob")
        r = client.get("/clients")
        names = [c["name"] for c in _json(r)]
        assert "Alice" in names
        assert "Bob" in names

    def test_create_client_no_program_allowed(self, client):
        r = client.post("/clients", json={"name": "No Program User"})
        assert r.status_code == 201

    def test_upsert_replaces_existing_client(self, client):
        _post_client(client, name="Repeat", weight=70)
        r = client.post("/clients", json={"name": "Repeat", "weight": 90, "program": "Beginner (BG)"})
        assert r.status_code == 201
        row = _json(client.get("/clients/Repeat"))
        assert row["weight"] == 90.0


# ---------------------------------------------------------------------------
# Progress Logging
# ---------------------------------------------------------------------------
class TestProgress:
    def test_log_progress_success(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/progress",
            json={"adherence": 80, "week": "Week 10 - 2026"},
        )
        assert r.status_code == 201

    def test_log_progress_missing_adherence_returns_400(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/progress", json={"week": "Week 1"})
        assert r.status_code == 400

    def test_log_progress_out_of_range_returns_400(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/progress", json={"adherence": 110})
        assert r.status_code == 400

    def test_log_progress_zero_adherence_allowed(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/progress", json={"adherence": 0})
        assert r.status_code == 201

    def test_log_progress_response_contains_week(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/progress",
            json={"adherence": 75, "week": "Week 5 - 2026"},
        )
        assert _json(r)["week"] == "Week 5 - 2026"


# ---------------------------------------------------------------------------
# Workout Logging
# ---------------------------------------------------------------------------
class TestWorkouts:
    def test_log_workout_success(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/workout",
            json={"date": "2026-03-09", "workout_type": "Strength", "duration_min": 60},
        )
        assert r.status_code == 201

    def test_log_workout_missing_date_returns_400(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/workout", json={"workout_type": "Strength"})
        assert r.status_code == 400

    def test_log_workout_missing_type_returns_400(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/workout", json={"date": "2026-03-09"})
        assert r.status_code == 400

    def test_log_workout_default_duration(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/workout",
            json={"date": "2026-03-09", "workout_type": "Cardio"},
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# Metrics Logging
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_log_metrics_success(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/metrics",
            json={"date": "2026-03-09", "weight": 79.5, "waist": 85.0, "bodyfat": 19.5},
        )
        assert r.status_code == 201

    def test_log_metrics_missing_date_returns_400(self, client):
        _post_client(client)
        r = client.post("/clients/Test Athlete/metrics", json={"weight": 79.5})
        assert r.status_code == 400

    def test_log_metrics_partial_data_allowed(self, client):
        _post_client(client)
        r = client.post(
            "/clients/Test Athlete/metrics",
            json={"date": "2026-03-09", "weight": 79.5},
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# BMI Calculator
# ---------------------------------------------------------------------------
class TestBMI:
    def test_bmi_normal_range(self, client):
        r = client.get("/bmi?height=175&weight=70")
        assert r.status_code == 200
        data = _json(r)
        assert data["category"] == "Normal"
        assert data["bmi"] == 22.9

    def test_bmi_underweight(self, client):
        r = client.get("/bmi?height=175&weight=50")
        assert _json(r)["category"] == "Underweight"

    def test_bmi_overweight(self, client):
        r = client.get("/bmi?height=175&weight=85")
        assert _json(r)["category"] == "Overweight"

    def test_bmi_obese(self, client):
        r = client.get("/bmi?height=175&weight=110")
        assert _json(r)["category"] == "Obese"

    def test_bmi_missing_params_returns_400(self, client):
        r = client.get("/bmi")
        assert r.status_code == 400

    def test_bmi_missing_weight_returns_400(self, client):
        r = client.get("/bmi?height=175")
        assert r.status_code == 400

    def test_bmi_zero_height_returns_400(self, client):
        r = client.get("/bmi?height=0&weight=70")
        assert r.status_code == 400

    def test_bmi_response_has_risk_field(self, client):
        data = _json(client.get("/bmi?height=175&weight=70"))
        assert "risk" in data


# ---------------------------------------------------------------------------
# Pure-function unit tests (no HTTP)
# ---------------------------------------------------------------------------
class TestComputeBMI:
    def test_normal_bmi_value(self):
        result = compute_bmi(175, 70)
        assert result["bmi"] == 22.9
        assert result["category"] == "Normal"

    def test_underweight_boundary(self):
        result = compute_bmi(175, 55)
        assert result["category"] == "Underweight"

    def test_overweight_boundary(self):
        result = compute_bmi(175, 80)
        assert result["category"] == "Overweight"

    def test_obese_boundary(self):
        result = compute_bmi(175, 105)
        assert result["category"] == "Obese"


class TestComputeCalories:
    def test_beginner_calories(self):
        assert compute_calories(80, "Beginner (BG)") == 2080

    def test_muscle_gain_calories(self):
        assert compute_calories(80, "Muscle Gain (MG) - PPL") == 2800

    def test_fat_loss_3day_calories(self):
        assert compute_calories(80, "Fat Loss (FL) - 3 day") == 1760

    def test_unknown_program_returns_none(self):
        assert compute_calories(80, "Unknown Program") is None

    def test_zero_weight_returns_none(self):
        assert compute_calories(0, "Beginner (BG)") is None


class TestProgramsData:
    def test_all_programs_have_positive_factor(self):
        for name, data in PROGRAMS.items():
            assert data["factor"] > 0, f"{name} has non-positive factor"

    def test_program_descriptions_not_empty(self):
        for name, data in PROGRAMS.items():
            assert data["desc"].strip(), f"{name} has empty description"

    def test_program_count(self):
        assert len(PROGRAMS) == 4
