from hashlib import sha256
from app.app_celery import celery_app

@celery_app.task(name='evidence.compute_sha256')
def compute_sha256(payload: bytes) -> str:
    return sha256(payload).hexdigest()
