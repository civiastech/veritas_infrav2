#!/usr/bin/env bash
set -euo pipefail
FILE=${1:?Usage: restore_postgres.sh <dump.sql>}
cat "$FILE" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-veritas}" -d "${POSTGRES_DB:-veritas}"
echo "Restore completed from $FILE"
