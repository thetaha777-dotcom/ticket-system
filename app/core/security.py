from datetime import datetime, timedelta
from jose.exceptions import JWTError, jwt
from passlib.context import CryptContext
from .config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.users.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Создание refresh токена"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """Декодирование токена"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        print(f"[AUTH DEBUG] Validating token: {token[:20]}...")

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        print(f"[AUTH DEBUG] Token payload - user_id: {user_id}")

        if user_id is None:
            print("[AUTH DEBUG] No user_id in token")
            raise credentials_exception

        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            print("[AUTH DEBUG] User not found in database")
            raise credentials_exception

        print(f"[AUTH DEBUG] User authenticated: {user.id}, {user.email}, Role: {user.role}")
        return user

    except JWTError as e:
        print(f"[AUTH DEBUG] JWT Error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"[AUTH DEBUG] Unexpected error: {e}")
        raise credentials_exception