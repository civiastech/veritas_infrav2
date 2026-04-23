#!/bin/sh
set -eu

echo "Starting Veritas backend..."
echo "Applying database migrations..."
alembic upgrade head

echo "Launching API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000