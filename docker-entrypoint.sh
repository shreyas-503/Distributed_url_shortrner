#!/bin/sh
echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI..."

echo "Starting Gunicorn + Uvicorn workers..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4