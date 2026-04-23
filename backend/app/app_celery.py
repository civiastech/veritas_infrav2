from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "veritas_infra",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=False,
    task_default_queue=settings.celery_queues,
    worker_concurrency=settings.celery_concurrency,
)

celery_app.autodiscover_tasks(["app"])


@celery_app.task(name="app.health.ping")
def ping() -> dict:
    return {"status": "ok"}