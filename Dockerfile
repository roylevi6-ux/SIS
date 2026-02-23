# ── SIS Backend (FastAPI + Uvicorn) ──────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY sis/ sis/
COPY config/ config/
COPY prompts/ prompts/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "sis.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
