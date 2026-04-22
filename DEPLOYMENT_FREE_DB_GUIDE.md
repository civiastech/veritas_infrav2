# Veritas Infra V3.1.5 Deployment Guide (Free / low-cost stack)

This build is designed to run in two practical ways:

## Option A — Single-domain deployment
- Backend + frontend behind one reverse proxy
- `frontend/config.js` stays at `API_BASE: '/api/v1'`
- Best when you deploy with Docker on one VM

## Option B — Split deployment with managed Postgres
- Static frontend on any static host
- FastAPI backend on any Python host
- Managed Postgres on Supabase, Neon, or any PostgreSQL provider
- `frontend/config.js` should point to your backend base URL, e.g. `https://api.example.com/api/v1`

## Minimum production variables
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS`
- `TRUSTED_HOSTS`
- `MINIO_*` values if you keep object storage enabled

## External Postgres example
```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres?sslmode=require
JWT_SECRET_KEY=replace-with-a-long-random-secret
CORS_ORIGINS=https://app.example.com,https://www.app.example.com
TRUSTED_HOSTS=app.example.com,www.app.example.com,api.example.com
AUTO_CREATE_TABLES=false
```

## Backend deploy sequence
1. Set environment variables
2. Run database migrations: `alembic upgrade head`
3. Seed baseline records: `python -m app.seed`
4. Start API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Frontend deploy sequence
1. Copy `frontend/config.example.js` to `frontend/config.js`
2. Set `API_BASE` correctly
3. Publish the `frontend/` folder on your static host

## Immediate launch recommendation
Use the current repo in this order:
1. Start from this V3.1.5 build
2. Use managed Postgres externally
3. Keep MinIO or replace with S3-compatible storage later
4. Use the seeded accounts only for first smoke testing, then rotate credentials

## Important pre-launch checks
- Change seeded/demo passwords
- Change `JWT_SECRET_KEY`
- Lock down CORS and trusted hosts
- Verify `/health`, `/ready`, login, project creation, evidence upload, inspection creation, and tender flow
