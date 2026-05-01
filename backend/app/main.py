from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import (
    academy,
    atlas,
    audit,
    auth,
    clone,
    components,
    dashboard,
    evidence,
    governance,
    lex,
    materials,
    monitor,
    notifications,
    payments,
    platformcfg,
    policy,
    professionals,
    projects,
    public,
    regulatory,
    seal,
    tenders,
    twin,
    verifund,
    vision,
    workflow,
)
from app.core.config import settings
from app.core.logging import JsonLoggingMiddleware
from app.db.base import Base
from app.db.session import engine
from app.services.storage import ensure_bucket


APP_VERSION = "v3.1.5-deployment-ready"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"

        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        is_https = request.url.scheme == "https" or forwarded_proto.lower() == "https"

        if settings.is_production and is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    if settings.minio_enabled:
        ensure_bucket()

    yield


app = FastAPI(
    title=settings.app_name,
    default_response_class=JSONResponse,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=None,
    lifespan=lifespan,
)

if settings.environment != "testing":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_host_list,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JsonLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.metrics_enabled:
    Instrumentator().instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
    )


@app.get("/health", include_in_schema=False)
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": APP_VERSION,
        "environment": settings.environment,
    }


@app.get("/ready", include_in_schema=False)
def ready():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "status": "ready",
        "database": "ok",
        "storage": "ok" if settings.minio_enabled else "disabled",
    }


ROUTERS = [
    auth.router,
    dashboard.router,
    professionals.router,
    projects.router,
    components.router,
    evidence.router,
    materials.router,
    tenders.router,
    notifications.router,
    audit.router,
    vision.router,
    twin.router,
    payments.router,
    seal.router,
    monitor.router,
    lex.router,
    public.router,
    atlas.router,
    verifund.router,
    academy.router,
    clone.router,
    governance.router,
    regulatory.router,
    workflow.router,
    policy.router,
    platformcfg.router,
]

for router in ROUTERS:
    app.include_router(router, prefix=settings.api_v1_str)

static_dir = Path(__file__).resolve().parent / "static"
uploads_dir = settings.uploads_path

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")