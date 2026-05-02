#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"

[[ -z "$DOMAIN" ]] && { echo "Usage: $0 <domain> <email>"; echo "Example: $0 app.veritas-infra.com admin@veritas-infra.com"; exit 1; }
[[ -z "$EMAIL" ]] && { echo "Usage: $0 <domain> <email>"; exit 1; }

echo "[+] Obtaining SSL certificate for $DOMAIN..."

# Stop nginx container if running (frees port 80 for standalone mode)
docker compose -f /opt/veritas/docker-compose.prod.yml stop nginx 2>/dev/null || true

certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Auto-renewal cron with nginx stop/start hooks
cat > /etc/cron.d/certbot-renew <<EOF
0 3 * * * root certbot renew --quiet \\
    --pre-hook  "docker compose -f /opt/veritas/docker-compose.prod.yml stop nginx" \\
    --post-hook "docker compose -f /opt/veritas/docker-compose.prod.yml start nginx"
EOF

echo ""
echo "✅ Certificate obtained successfully!"
echo "   Cert: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "   Key:  /etc/letsencrypt/live/$DOMAIN/privkey.pem"
