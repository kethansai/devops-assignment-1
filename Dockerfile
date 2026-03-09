# ---------------------------------------------------------------------------
# Dockerfile — ACEest Fitness & Gym Management
# Multi-stage-style slim image for security and size efficiency
# ---------------------------------------------------------------------------

# Base: official Python 3.11 slim (Debian bookworm, no dev tools)
FROM python:3.11-slim

# Metadata
LABEL maintainer="ACEest DevOps Team" \
      version="3.2.4" \
      description="ACEest Fitness & Gym Flask API"

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Install dependencies first (layer caching — only re-runs on requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source and tests
COPY app.py .
COPY tests/ ./tests/

# Switch to non-root user
USER appuser

EXPOSE 5000

# Default: run the Flask application
CMD ["python", "app.py"]
