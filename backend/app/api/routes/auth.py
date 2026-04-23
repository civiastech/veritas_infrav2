import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    build_totp_uri,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    verify_password,
    verify_totp,
)
from app.db.session import get_db
from app.models.entities import AuthAttempt, Professional, RefreshToken
from app.schemas.api import (
    MFASetupResponse,
    MFAVerifyRequest,
    LoginRequest,
    ProfessionalOut,
    RefreshRequest,
    TokenPair,
)
from app.services.audit import record_audit
from app.services.rate_limit import allow

router = APIRouter(prefix="/auth", tags=["auth"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_locked(user: Professional) -> bool:
    return bool(user.locked_until and user.locked_until > utcnow())


def _record_auth_attempt(
    db: Session,
    *,
    email: str,
    ip_address: str | None,
    success: bool,
    reason: str,
) -> None:
    db.add(
        AuthAttempt(
            email=email,
            ip_address=ip_address,
            success=success,
            reason=reason,
        )
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    email = normalize_email(payload.email)

    if not allow(f"login:{ip or 'unknown'}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please retry later.",
        )

    user = (
        db.query(Professional)
        .filter(
            Professional.email == email,
            Professional.is_deleted.is_(False),
        )
        .first()
    )

    if not user:
        _record_auth_attempt(
            db,
            email=email,
            ip_address=ip,
            success=False,
            reason="missing_user",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not getattr(user, "active", True):
        _record_auth_attempt(
            db,
            email=email,
            ip_address=ip,
            success=False,
            reason="inactive_user",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    if _is_locked(user):
        _record_auth_attempt(
            db,
            email=email,
            ip_address=ip,
            success=False,
            reason="locked",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked",
        )

    if not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        current_attempts = user.failed_login_attempts or 0
        user.failed_login_attempts = current_attempts + 1

        if user.failed_login_attempts >= settings.account_lock_threshold:
            user.locked_until = utcnow() + timedelta(minutes=settings.account_lock_minutes)

        _record_auth_attempt(
            db,
            email=email,
            ip_address=ip,
            success=False,
            reason="bad_password",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if user.mfa_enabled:
        if not payload.mfa_code or not user.mfa_secret or not verify_totp(payload.mfa_code, user.mfa_secret):
            _record_auth_attempt(
                db,
                email=email,
                ip_address=ip,
                success=False,
                reason="bad_mfa",
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required or invalid",
            )

    user.failed_login_attempts = 0
    user.locked_until = None

    refresh_id = secrets.token_hex(16)
    refresh = RefreshToken(
        token_id=refresh_id,
        professional_id=user.id,
        expires_at=utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes),
        revoked=False,
    )

    db.add(refresh)
    _record_auth_attempt(
        db,
        email=email,
        ip_address=ip,
        success=True,
        reason="ok",
    )
    db.commit()

    access_token = create_access_token(
        user.email,
        user.role,
        extra={"mfa": bool(user.mfa_enabled)},
    )
    refresh_token = create_refresh_token(user.email, user.role, refresh_id)

    try:
        record_audit(
            db,
            user.email,
            "AUTH_LOGIN",
            "User authenticated successfully",
            ip_address=ip,
            route=str(request.url.path),
        )
    except Exception as exc:
        print(f"Audit log failed during login: {exc}")

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("typ") != "refresh":
            raise ValueError("wrong token type")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    token_id = decoded.get("jti")
    if not token_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    stored = db.query(RefreshToken).filter(RefreshToken.token_id == token_id).first()
    if not stored or stored.revoked or stored.expires_at < utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked",
        )

    user = (
        db.query(Professional)
        .filter(
            Professional.id == stored.professional_id,
            Professional.is_deleted.is_(False),
        )
        .first()
    )
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User unavailable",
        )

    stored.revoked = True

    new_refresh_id = secrets.token_hex(16)
    replacement = RefreshToken(
        token_id=new_refresh_id,
        professional_id=user.id,
        expires_at=utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes),
        revoked=False,
    )
    db.add(replacement)
    db.commit()

    access_token = create_access_token(
        user.email,
        user.role,
        extra={"mfa": bool(user.mfa_enabled)},
    )
    refresh_token = create_refresh_token(user.email, user.role, new_refresh_id)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(
    current_user: Professional = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    secret = generate_totp_secret()
    current_user.mfa_secret = secret
    current_user.mfa_enabled = False
    db.commit()

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=build_totp_uri(current_user.email, secret),
    )


@router.post("/mfa/verify")
def verify_mfa(
    payload: MFAVerifyRequest,
    current_user: Professional = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.mfa_secret or not verify_totp(payload.code, current_user.mfa_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    current_user.mfa_enabled = True
    db.commit()

    return {
        "success": True,
        "message": "MFA enabled",
    }


@router.get("/me", response_model=ProfessionalOut)
def me(current_user: Professional = Depends(get_current_user)):
    return current_user