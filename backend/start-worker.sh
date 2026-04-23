#!/bin/sh
set -e

echo "Starting Celery worker..."
exec celery -A app.app_celery.celery_app worker --loglevel=info