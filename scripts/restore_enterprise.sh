#!/usr/bin/env bash
set -euo pipefail
sql_file="$1"
docker compose exec -T postgres psql -U ${POSTGRES_USER:-veritas} -d ${POSTGRES_DB:-veritas} < "$sql_file"
echo "Database restore complete"
