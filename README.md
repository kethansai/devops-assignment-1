# ACEest Fitness & Gym Management System

A **Flask REST API** for fitness and gym management — built as part of a DevOps CI/CD pipeline assignment.  
The project demonstrates Version Control (Git/GitHub), Containerization (Docker), and automated pipelines via **GitHub Actions** and **Jenkins**.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Local Setup & Execution](#local-setup--execution)
3. [API Endpoints](#api-endpoints)
4. [Running Tests Manually](#running-tests-manually)
5. [Docker Usage](#docker-usage)
6. [GitHub Actions Pipeline](#github-actions-pipeline)
7. [Jenkins BUILD Integration](#jenkins-build-integration)
8. [Version History](#version-history)

---

## Project Structure

```
aceest-fitness-devops/
├── app.py                      # Flask REST API application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── Jenkinsfile                 # Jenkins declarative pipeline
├── .github/
│   └── workflows/
│       └── main.yml            # GitHub Actions CI/CD workflow
├── tests/
│   ├── __init__.py
│   └── test_app.py             # Pytest test suite (50+ tests)
└── README.md                   # This file
```

---

## Local Setup & Execution

### Prerequisites

- Python 3.11+
- pip
- (Optional) Docker Desktop

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/aceest-fitness-devops.git
cd aceest-fitness-devops
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Flask application

```bash
python app.py
```

The API will be available at **http://localhost:5000**.

### 5. Quick smoke test

```bash
curl http://localhost:5000/
curl http://localhost:5000/programs
curl "http://localhost:5000/bmi?height=175&weight=70"
```

---

## API Endpoints

| Method | Endpoint                       | Description                      |
| ------ | ------------------------------ | -------------------------------- |
| `GET`  | `/`                            | Application info & endpoint list |
| `GET`  | `/programs`                    | List all fitness programs        |
| `GET`  | `/programs/<name>`             | Get a single program             |
| `GET`  | `/clients`                     | List all clients                 |
| `POST` | `/clients`                     | Create / update a client         |
| `GET`  | `/clients/<name>`              | Get a single client              |
| `POST` | `/clients/<name>/progress`     | Log weekly adherence             |
| `POST` | `/clients/<name>/workout`      | Log a workout session            |
| `POST` | `/clients/<name>/metrics`      | Log body metrics                 |
| `GET`  | `/bmi?height=<cm>&weight=<kg>` | Calculate BMI                    |

### Example — Create a client

```bash
curl -X POST http://localhost:5000/clients \
     -H "Content-Type: application/json" \
     -d '{"name":"Arjun","age":28,"height":178,"weight":82,"program":"Muscle Gain (MG) - PPL"}'
```

### Example — Log progress

```bash
curl -X POST http://localhost:5000/clients/Arjun/progress \
     -H "Content-Type: application/json" \
     -d '{"adherence": 85, "week": "Week 10 - 2026"}'
```

---

## Running Tests Manually

### Run the full Pytest suite

```bash
pytest tests/ -v
```

### Run with coverage report

```bash
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run a specific test class

```bash
pytest tests/test_app.py::TestBMI -v
pytest tests/test_app.py::TestClients -v
```

The test suite uses a **temporary SQLite database** for every test run, so your production data is never affected.

---

## Docker Usage

### Build the image

```bash
docker build -t aceest-fitness:latest .
```

### Run the container

```bash
docker run -p 5000:5000 aceest-fitness:latest
```

### Run tests inside the container

```bash
docker run --rm aceest-fitness:latest pytest tests/ -v
```

### Image design decisions

- Based on **python:3.11-slim** (Debian) — minimal attack surface, no build tools.
- Dependencies installed before source copy for **layer cache efficiency**.
- Application runs as a **non-root user** (`appuser`) for security.
- `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` set as environment variables.

---

## GitHub Actions Pipeline

The pipeline is defined in **`.github/workflows/main.yml`** and is triggered on every `push` or `pull_request` to the `main` and `develop` branches.

### Pipeline Stages

```
push / pull_request
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 1 — Build & Lint                              │
│  • actions/setup-python@v5 (Python 3.11)             │
│  • pip install -r requirements.txt                   │
│  • flake8 app.py --max-line-length=120               │
│  • Verify clean import of application module         │
└──────────────────────┬───────────────────────────────┘
                       │ (needs: build-and-lint)
                       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 2 — Docker Image Assembly                     │
│  • docker build -t aceest-fitness:<SHA> .            │
│  • docker build -t aceest-fitness:latest .           │
│  • Inspect final image size                          │
└──────────────────────┬───────────────────────────────┘
                       │ (needs: docker-build)
                       ▼
┌──────────────────────────────────────────────────────┐
│  Stage 3 — Automated Testing                         │
│  • Build Docker image for testing                    │
│  • docker run pytest tests/ -v --tb=short            │
│  • All 50+ tests must pass to mark build green       │
└──────────────────────────────────────────────────────┘
```

The pipeline uses **job dependencies** (`needs:`) to ensure stages run sequentially and a failure in any early stage stops the rest.

---

## Jenkins BUILD Integration

The **`Jenkinsfile`** at the repository root defines a declarative pipeline for the Jenkins BUILD phase quality gate.

### Setup Instructions

1. **Install Jenkins** (local or server) with the following plugins:
   - Pipeline
   - Git
   - Docker Pipeline

2. **Create a new Pipeline job** in Jenkins:
   - Dashboard → New Item → Pipeline
   - Name: `aceest-fitness-build`

3. **Configure SCM** in the Pipeline section:
   - Definition: _Pipeline script from SCM_
   - SCM: Git
   - Repository URL: `https://github.com/<your-username>/aceest-fitness-devops.git`
   - Script Path: `Jenkinsfile`

4. **Trigger the build**: Click _Build Now_ or enable webhook triggers from GitHub.

### Jenkins Pipeline Stages

| Stage              | Action                                            |
| ------------------ | ------------------------------------------------- |
| Checkout           | Pull latest code from GitHub                      |
| Build Environment  | `pip install -r requirements.txt`                 |
| Lint               | `flake8 app.py` syntax & style check              |
| Build Docker Image | `docker build -t aceest-fitness:<BUILD_NUMBER> .` |
| Run Tests          | `docker run pytest tests/ -v --tb=short`          |
| Clean Up           | Remove intermediate Docker image                  |

On **success**, the console logs `✅ BUILD SUCCEEDED — All stages passed`.  
On **failure**, it logs `❌ BUILD FAILED` with the offending stage clearly identified.

---

## Version History

| Version       | File                 | Changes                                         |
| ------------- | -------------------- | ----------------------------------------------- |
| 1.0           | `Aceestver-1.0.py`   | Initial tkinter UI — program display only       |
| 1.1           | `Aceestver-1.1.py`   | Added calorie calculator & input forms          |
| 2.1.2         | `Aceestver-2.1.2.py` | SQLite integration for client storage           |
| 2.2.1         | `Aceestver-2.2.1.py` | Progress tracking & weekly adherence            |
| 2.2.4         | `Aceestver-2.2.4.py` | Weight trend charts (matplotlib)                |
| 3.0.1         | `Aceestver-3.0.1.py` | Full login system & role-based access           |
| 3.1.2         | `Aceestver-3.1.2.py` | Workout + exercise logging, PDF reports         |
| 3.2.4         | `Aceestver-3.2.4.py` | Full desktop app — body metrics, BMI analytics  |
| **Flask API** | `app.py`             | Migration to Flask REST API for DevOps pipeline |

---

## Author

**ACEest Fitness & Gym — DevOps Assignment**  
Introduction to DevOps — 2026
