#!/bin/sh
set -eu

echo "Starting Veritas backend..."
echo "Environment: ${ENVIRONMENT:-production}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set"
  exit 1
fi

RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
  echo "Database migrations complete."
else
  echo "Skipping migrations (RUN_MIGRATIONS=false)"
fi

HOST="${UVICORN_HOST:-0.0.0.0}"
PORT="${UVICORN_PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

echo "Launching API server on ${HOST}:${PORT} with ${WORKERS} worker(s)..."

if [ "$WORKERS" -gt 1 ] 2>/dev/null; then
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
else
  exec uvicorn app.main:app --host "$HOST" --port "$PORT"
fi