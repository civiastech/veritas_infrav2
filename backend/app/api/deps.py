from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models.entities import Professional, RefreshToken
from app.services.authz import ensure_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Professional:
    try:
        payload = decode_token(token)
        email = payload.get('sub')
        if payload.get('typ') != 'access' or not email:
            raise ValueError('invalid token type or missing subject')
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication credentials') from exc
    user = db.query(Professional).filter(Professional.email == email, Professional.is_deleted.is_(False)).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Inactive or missing user')
    return user


def require_roles(*roles: str):
    def checker(user: Professional = Depends(get_current_user)) -> Professional:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
        return user
    return checker


def require_action(action: str, project_uid_param: str | None = None):
    def checker(request: Request, db: Session = Depends(get_db), user: Professional = Depends(get_current_user)) -> Professional:
        project_uid = request.path_params.get(project_uid_param) if project_uid_param else request.query_params.get('project_uid')
        ensure_permission(db, user, action, project_uid)
        return user
    return checker


def pagination(skip: int = 0, limit: int = 50) -> tuple[int, int]:
    limit = min(max(limit, 1), 200)
    skip = max(skip, 0)
    return skip, limit
