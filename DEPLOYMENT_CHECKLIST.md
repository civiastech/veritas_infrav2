
# Deployment Checklist

## Before first live deployment

- Change all default secrets in `.env`
- Restrict `TRUSTED_HOSTS` and `CORS_ORIGINS`
- Place Nginx behind TLS
- Set backup schedule for Postgres and MinIO
- Verify Grafana admin password
- Confirm storage capacity for uploads/evidence
- Disable wildcard hosts in production
- Review default admin bootstrap credentials

## Smoke validation

- `/health` returns 200
- `/ready` returns 200
- `/api/v1/docs` loads
- MinIO bucket exists
- worker is connected to Redis
- Grafana can query Prometheus
