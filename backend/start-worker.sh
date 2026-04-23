#!/bin/sh
set -eu

echo "Starting Veritas Celery worker..."
echo "Environment: ${ENVIRONMENT:-production}"

if [ -z "${REDIS_URL:-}" ]; then
  echo "ERROR: REDIS_URL is not set"
  exit 1
fi

CONCURRENCY="${CELERY_CONCURRENCY:-2}"
LOGLEVEL="${CELERY_LOGLEVEL:-info}"
QUEUES="${CELERY_QUEUES:-celery}"

echo "Config:"
echo "  Concurrency: $CONCURRENCY"
echo "  Queues: $QUEUES"
echo "  LogLevel: $LOGLEVEL"

exec celery \
  -A app.app_celery.celery_app worker \
  --loglevel="$LOGLEVEL" \
  --concurrency="$CONCURRENCY" \
  --queues="$QUEUES" \
  --hostname="veritas_worker@%h" \
  --without-gossip \
  --without-mingle \
  --without-heartbeat \
  --max-tasks-per-child=100 \
  --prefetch-multiplier=1