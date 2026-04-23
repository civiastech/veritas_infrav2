# 🟡 VERITAS INFRA  
### Institutional Infrastructure Intelligence Platform

![Status](https://img.shields.io/badge/status-stabilization--checkpoint-gold)
![Version](https://img.shields.io/badge/version-v3.1.5-black)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Database](https://img.shields.io/badge/database-PostgreSQL-336791)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)
![Monitoring](https://img.shields.io/badge/observability-Prometheus%20%7C%20Grafana-orange)
![License](https://img.shields.io/badge/license-proprietary-red)

---

## 🔥 Overview

**Veritas Infra** is a **deployment-grade infrastructure operating system** that unifies:

- Execution  
- Compliance  
- Financial flows  
- Governance  
- Intelligence  

into a single, verifiable platform.

> This is not a dashboard.  
> This is not CRUD software.  
>  
> **This is infrastructure made accountable.**

---

## 🧠 Core Philosophy

Every action in infrastructure must be:

- **Traceable**
- **Verifiable**
- **Governed**

The system enforces:

- Evidence-backed execution  
- Real-time validation  
- Institutional oversight  
- Full lifecycle traceability  

---

## 🧩 Platform Architecture

The platform is structured as a layered institutional system:

- Core control layer  
- Execution modules  
- Governance & regulatory layer  
- Intelligence layer (ATLAS)

![Veritas Infra Architecture](docs/architecture.svg)

---

## 🧩 Module System

| Module | Purpose |
|------|--------|
| IDENT | Professional identity & verification |
| TWIN | Project lifecycle & digital twin |
| BUILD | Evidence & validation |
| VISION | Inspections & condition tracking |
| PAY | Financial flows & milestones |
| SEAL | Certifications |
| MARKET | Tenders |
| ORIGIN | Material traceability |
| MONITOR | Sensors & alerts |
| LEX | Disputes & legal tracking |
| ATLAS | Portfolio intelligence |
| VERIFUND | Financial instruments |
| ACADEMY | Learning & credentials |
| GOVERNANCE | Oversight & committees |
| REGULATORY | Compliance intelligence |
| CLONE | Deployment replication |

---

## 🏗️ Enterprise UI Completion

The frontend is aligned with the original institutional prototype and now supports:

- Governance  
- Regulatory  
- Payments  
- Certification (Seal)  
- Disputes (Lex)  
- Monitoring  
- Atlas intelligence  
- Academy (paths, courses, credentials)  
- Policy & workflow  
- Platform configuration  

### Key Improvements

- Prototype UI is now **API-connected**
- Control-plane actions exposed in dashboard
- Backend routes aligned with `/api/v1`

---

## ⚙️ System Stack

| Layer | Technology |
|------|-----------|
| Frontend | HTML / JS / CSS (Prototype-aligned) |
| Backend | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Cache / Queue | Redis |
| Object Storage | MinIO |
| Reverse Proxy | Nginx |
| Monitoring | Prometheus + Grafana |
| Containerization | Docker Compose |

---

## 🚀 Quick Start

```bash
cp .env.example .env
docker compose up --build -d