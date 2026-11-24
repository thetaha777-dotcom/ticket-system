import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_token, decode_token
from app.shared.exceptions import Forbidden, Unauthorized
from app.users.models import User, UserRole

# tokenUrl powers the "Authorize" button in the interactive docs (/docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def create_access_token(user_id: uuid.UUID) -> str:
    return create_token(subject=str(user_id), purpose="access", expires_mins=settings.access_token_expire_mins)


def get_optional_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    payload = decode_token(token, purpose="access")
    if not payload:
        return None
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError):
        return None
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise Unauthorized("Sign in to continue", "not_authenticated")
    return user


def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise Forbidden("You do not have permission for this action", "insufficient_role")
        return user

    return dependency


require_organizer = require_roles(UserRole.ORGANIZER, UserRole.PLATFORM_ADMIN)
require_admin = require_roles(UserRole.PLATFORM_ADMIN)
