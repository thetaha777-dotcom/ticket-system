import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Session

from app.users.models import User
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_token, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(user_id: uuid.UUID) -> str:
    return create_token(subject=str(user_id), purpose="access", expires_mins=settings.access_token_expire_mins,)

def get_current_user(
    token: str=Depends(oauth2_scheme), db: Session=Depends(get_db),
) -> User:
    cred_error = HTTPException(

    )