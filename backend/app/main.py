
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.core.logging import JsonLoggingMiddleware
from app.db.base import Base
from app.db.session import engine
from app.api.routes import (
    auth, dashboard, professionals, projects, components, evidence, materials, tenders,
    notifications, audit, vision, twin, payments, seal, monitor, lex, public, atlas, verifund, academy,
    clone, governance, regulatory, workflow, policy, platformcfg
)
from app.services.storage import ensure_bucket

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app = FastAPI(
    title=settings.app_name,
    default_response_class=JSONResponse,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(JsonLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)

if settings.metrics_enabled:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

@app.on_event("startup")
def startup_event():
    ensure_bucket()

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": "v3.1.5-deployment-ready"}

@app.get("/ready")
def ready():
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return {"status": "ready"}

for r in [
    auth.router, dashboard.router, professionals.router, projects.router, components.router, evidence.router,
    materials.router, tenders.router, notifications.router, audit.router, vision.router, twin.router,
    payments.router, seal.router, monitor.router, lex.router, public.router, atlas.router, verifund.router, academy.router, clone.router, governance.router, regulatory.router, workflow.router, policy.router, platformcfg.router
]:
    app.include_router(r, prefix=settings.api_v1_str)

static_dir = Path(__file__).resolve().parent / "static"
uploads_dir = Path(settings.uploads_dir)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
