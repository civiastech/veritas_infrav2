#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

[[ -f "$ENV_FILE" ]] || { echo "Error: $ENV_FILE not found. Run: cp .env.production.example .env.production"; exit 1; }

gen_hex()  { openssl rand -hex 32; }
gen_pass() { openssl rand -base64 24 | tr -d '=/+' | head -c 24; }

echo "[+] Generating secrets into $ENV_FILE..."

sed -i "s|REPLACE_JWT_SECRET|$(gen_hex)|g"          "$ENV_FILE"
sed -i "s|REPLACE_POSTGRES_PASSWORD|$(gen_pass)|g"  "$ENV_FILE"
sed -i "s|REPLACE_ADMIN_PASSWORD|$(gen_pass)|g"     "$ENV_FILE"
sed -i "s|REPLACE_MINIO_USER|veritas-$(gen_pass | head -c 8)|g"  "$ENV_FILE"
sed -i "s|REPLACE_MINIO_PASSWORD|$(gen_pass)|g"     "$ENV_FILE"
sed -i "s|REPLACE_GRAFANA_PASSWORD|$(gen_pass)|g"   "$ENV_FILE"

echo "[+] Secrets generated. Now edit $ENV_FILE and set:"
echo "    DOMAIN, CORS_ORIGINS, TRUSTED_HOSTS, FIRST_SUPERUSER_EMAIL, SEAL_REGISTRY_URL"
