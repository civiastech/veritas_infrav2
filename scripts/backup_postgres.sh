#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
OUTDIR=${1:-./backups}
mkdir -p "$OUTDIR"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-veritas}" -d "${POSTGRES_DB:-veritas}" > "$OUTDIR/veritas_${STAMP}.sql"
echo "Backup written to $OUTDIR/veritas_${STAMP}.sql"
