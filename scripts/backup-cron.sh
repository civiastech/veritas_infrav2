#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="/opt/veritas"
BACKUP_DIR="$DEPLOY_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE="docker compose -f $DEPLOY_DIR/docker-compose.prod.yml"

mkdir -p "$BACKUP_DIR"

echo "[+] Starting backup at $TIMESTAMP..."

# PostgreSQL
echo "[+] Backing up PostgreSQL..."
$COMPOSE exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-veritas}" \
    "${POSTGRES_DB:-veritas}" \
    | gzip > "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"
echo "[+] Postgres backup: postgres_$TIMESTAMP.sql.gz"

# MinIO (tar the Docker volume)
echo "[+] Backing up MinIO data..."
docker run --rm \
    --volumes-from veritas_minio \
    -v "$BACKUP_DIR:/backup" \
    alpine tar czf "/backup/minio_$TIMESTAMP.tar.gz" /data
echo "[+] MinIO backup: minio_$TIMESTAMP.tar.gz"

# Checksums
sha256sum "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz" \
          "$BACKUP_DIR/minio_$TIMESTAMP.tar.gz" \
    > "$BACKUP_DIR/checksums_$TIMESTAMP.sha256"

# Retain last 14 days only
find "$BACKUP_DIR" -name "*.sql.gz"   -mtime +14 -delete
find "$BACKUP_DIR" -name "*.tar.gz"   -mtime +14 -delete
find "$BACKUP_DIR" -name "*.sha256"   -mtime +14 -delete

echo ""
echo "[+] Backup complete."
ls -lh "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null || true
