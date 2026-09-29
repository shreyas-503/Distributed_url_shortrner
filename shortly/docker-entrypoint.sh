#!/bin/sh

echo "Running database migrations..."

alembic upgrade head

echo "Starting FastAPI..."

exec "$@"