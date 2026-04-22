#!/usr/bin/env bash
set -euo pipefail
mkdir -p backups
stamp=$(date +%Y%m%d_%H%M%S)
docker compose exec -T postgres pg_dump -U ${POSTGRES_USER:-veritas} ${POSTGRES_DB:-veritas} > backups/postgres_${stamp}.sql
docker compose exec -T minio sh -c 'tar -czf - /data' > backups/minio_${stamp}.tar.gz
echo "Backups written to ./backups"
