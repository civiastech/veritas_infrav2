## Enterprise UI Completion Pass
- Canonical prototype frontend expanded to cover clone, governance, regulatory, pay, seal, lex, monitor, atlas, academy, policy, platform configuration, and workflow operations.
- Enterprise control-plane actions exposed in the dashboard and module screens.
- Live API paths corrected to backend route prefixes.

# Veritas Infra v3.1.3 Prototype-Live Unified Master

# Veritas Infra V3.1.2 Prototype-Aligned Master

This repository is the merged final baseline built to align as closely as possible to the original institutional prototype while preserving the strongest real-world deployment spine from the V3.1.0 master.

## What this build does

- keeps the **full V3 operational backend** and deployment stack
- promotes the **original prototype HTML** to the canonical frontend entrypoint in `frontend/index.html`
- preserves the lighter API-facing operational console as `frontend/ops_console.html`
- retains Docker Compose, PostgreSQL, Redis, MinIO, Nginx, Prometheus, Grafana, migrations, seeding, and tests
- includes documentation showing how the prototype doctrine maps to backend modules

## Why this version exists

The original prototype captured the doctrine, institutional tone, module language, and full-platform imagination better than the later minimal SPA. The V3 backend captured the deployable runtime spine better than the prototype. This repo combines both.

## Canonical user-facing entrypoints

- `frontend/index.html` → original prototype-aligned institutional experience
- `frontend/ops_console.html` → lighter authenticated operational console bound to `/api/v1`
- `frontend/prototype_reference.html` → frozen reference copy of the original prototype

## Included business/API areas

Operational backend APIs:

- Auth / RBAC
- Dashboard
- Projects / Components / Evidence
- Vision / Twin / Payments / Seal
- Monitor / Lex / Atlas / Verifund
- Academy / Clone / Governance / Regulatory
- Workflow / Policy / Platform / Country configuration

## Quick start

```bash
cp .env.example .env
docker compose up --build -d
```

Open:

- http://localhost
- http://localhost/health
- http://localhost/api/v1/docs
- http://localhost/ops_console.html
- http://localhost:3001 (Grafana)
- http://localhost:9001 (MinIO console)

## Important note

This is the strongest merged baseline available from the supplied repos and prototype. It is **the closest practical alignment** to the original HTML vision, but it does **not** claim that every prototype interaction has been fully re-engineered into the backend/API layer. The prototype remains the canonical institutional experience, while the operational backend provides the deployable system spine.


## Frontend status

The primary frontend at `/` is now a live API-backed institutional console aligned to the original prototype doctrine. It authenticates against the backend and supports live reads plus key write flows for projects, components, evidence, inspections, tenders, ATLAS reports, VERIFUND products/applications, and ACADEMY paths/courses.
