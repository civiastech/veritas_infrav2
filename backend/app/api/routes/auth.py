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
from app.schemas.api import MFASetupResponse, MFAVerifyRequest, LoginRequest, ProfessionalOut, RefreshRequest, TokenPair
from app.services.audit import record_audit
from app.services.rate_limit import allow

router = APIRouter(prefix='/auth', tags=['auth'])


def _is_locked(user: Professional) -> bool:
    return bool(user.locked_until and user.locked_until > datetime.now(timezone.utc))


@router.post('/login', response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    if not allow(f'login:{ip or "unknown"}'):
        raise HTTPException(status_code=429, detail='Too many login attempts. Please retry later.')

    user = db.query(Professional).filter(
        Professional.email == payload.email,
        Professional.is_deleted.is_(False)
    ).first()

    if not user:
        db.add(AuthAttempt(email=payload.email, ip_address=ip, success=False, reason='missing_user'))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

    if _is_locked(user):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail='Account temporarily locked')

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.account_lock_threshold:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.account_lock_minutes)
        db.add(AuthAttempt(email=payload.email, ip_address=ip, success=False, reason='bad_password'))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

    if user.mfa_enabled:
        if not payload.mfa_code or not user.mfa_secret or not verify_totp(payload.mfa_code, user.mfa_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='MFA code required or invalid')

    user.failed_login_attempts = 0
    user.locked_until = None

    refresh_id = secrets.token_hex(16)
    refresh = RefreshToken(
        token_id=refresh_id,
        professional_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes),
    )

    db.add(refresh)
    db.add(AuthAttempt(email=payload.email, ip_address=ip, success=True, reason='ok'))
    db.commit()

    access_token = create_access_token(user.email, user.role, extra={'mfa': user.mfa_enabled})
    refresh_token = create_refresh_token(user.email, user.role, refresh_id)

    try:
        record_audit(
            db,
            user.email,
            'AUTH_LOGIN',
            'User authenticated successfully',
            ip_address=ip,
            route=str(request.url.path),
        )
    except Exception as exc:
        print(f'Audit log failed during login: {exc}')

    return TokenPair(access_token=access_token, refresh_token=refresh_token)

@router.post('/refresh', response_model=TokenPair)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get('typ') != 'refresh':
            raise ValueError('wrong token type')
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Invalid refresh token') from exc
    stored = db.query(RefreshToken).filter(RefreshToken.token_id == decoded['jti']).first()
    if not stored or stored.revoked or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail='Refresh token expired or revoked')
    user = db.query(Professional).filter(Professional.id == stored.professional_id).first()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail='User unavailable')
    access_token = create_access_token(user.email, user.role, extra={'mfa': user.mfa_enabled})
    new_refresh_id = secrets.token_hex(16)
    stored.revoked = True
    replacement = RefreshToken(token_id=new_refresh_id, professional_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes))
    db.add(replacement)
    db.commit()
    return TokenPair(access_token=access_token, refresh_token=create_refresh_token(user.email, user.role, new_refresh_id))


@router.post('/mfa/setup', response_model=MFASetupResponse)
def setup_mfa(current_user: Professional = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = generate_totp_secret()
    current_user.mfa_secret = secret
    db.commit()
    return MFASetupResponse(secret=secret, provisioning_uri=build_totp_uri(current_user.email, secret))


@router.post('/mfa/verify')
def verify_mfa(payload: MFAVerifyRequest, current_user: Professional = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.mfa_secret or not verify_totp(payload.code, current_user.mfa_secret):
        raise HTTPException(status_code=400, detail='Invalid MFA code')
    current_user.mfa_enabled = True
    db.commit()
    return {'success': True, 'message': 'MFA enabled'}


@router.get('/me', response_model=ProfessionalOut)
def me(current_user: Professional = Depends(get_current_user)):
    return current_user
