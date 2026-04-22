import hashlib
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from app.core.config import settings


def ensure_upload_dir(subdir: str) -> Path:
    path = Path(settings.uploads_dir) / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_upload(file: UploadFile, subdir: str) -> tuple[str, str, int]:
    dest_dir = ensure_upload_dir(subdir)
    suffix = Path(file.filename or '').suffix
    safe_name = f"{uuid4().hex}{suffix}"
    dest = dest_dir / safe_name
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    dest.write_bytes(content)
    return str(dest), sha256, len(content)
