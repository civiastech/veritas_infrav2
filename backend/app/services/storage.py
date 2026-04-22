from __future__ import annotations
import io
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from app.core.config import settings


def get_minio_client() -> Minio | None:
    if not settings.minio_enabled:
        return None
    try:
        return Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    except Exception:
        return None


def ensure_bucket() -> None:
    client = get_minio_client()
    if not client:
        return
    try:
        exists = client.bucket_exists(settings.minio_bucket_evidence)
        if not exists:
            client.make_bucket(settings.minio_bucket_evidence)
    except Exception:
        return


def store_object(object_name: str, payload: bytes, content_type: str = 'application/octet-stream') -> tuple[str, str]:
    client = get_minio_client()
    if client:
        try:
            ensure_bucket()
            client.put_object(
                settings.minio_bucket_evidence,
                object_name,
                io.BytesIO(payload),
                len(payload),
                content_type=content_type,
            )
            return 'minio', f's3://{settings.minio_bucket_evidence}/{object_name}'
        except S3Error:
            pass
        except Exception:
            pass
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / object_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return 'filesystem', f'/uploads/{object_name}'
