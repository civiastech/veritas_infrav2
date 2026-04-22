import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
import pyotp
from app.core.config import settings


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def _unb64(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def get_password_hash(password: str) -> str:
    iterations = 310000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), iterations)
    return f'pbkdf2_sha256${iterations}${salt}${_b64(digest)}'


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith('pbkdf2_sha256$'):
        _, iterations, salt, digest = hashed_password.split('$', 3)
        candidate = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(_b64(candidate), digest)
    legacy_salt = hashlib.sha256(settings.jwt_secret_key.encode()).digest()[:16]
    digest = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), legacy_salt, 200000)
    return hmac.compare_digest(_b64(digest), hashed_password)


def _encode_token(payload: dict[str, Any]) -> str:
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
    sig = hmac.new(settings.jwt_secret_key.encode(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64(payload_bytes)}.{_b64(sig)}"


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        'typ': 'access',
        'sub': subject,
        'role': role,
        'jti': secrets.token_hex(12),
        'exp': int(expire.timestamp()),
        'iat': int(datetime.now(timezone.utc).timestamp()),
    }
    if extra:
        payload.update(extra)
    return _encode_token(payload)


def create_refresh_token(subject: str, role: str, token_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)
    payload = {
        'typ': 'refresh',
        'sub': subject,
        'role': role,
        'jti': token_id,
        'exp': int(expire.timestamp()),
        'iat': int(datetime.now(timezone.utc).timestamp()),
    }
    return _encode_token(payload)


def decode_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split('.')
        payload_bytes = _unb64(payload_b64)
        expected_sig = hmac.new(settings.jwt_secret_key.encode(), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _unb64(sig_b64)):
            raise ValueError('Invalid signature')
        payload = json.loads(payload_bytes.decode())
        if int(payload['exp']) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError('Token expired')
        return payload
    except Exception as exc:
        raise ValueError('Invalid token') from exc


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_totp_uri(email: str, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.mfa_issuer)


def verify_totp(code: str, secret: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
