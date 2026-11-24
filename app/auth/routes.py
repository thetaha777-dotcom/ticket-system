from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import services
from app.auth.dependencies import create_access_token, get_current_user
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    Message,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.core.database import get_db
from app.users.models import User
from app.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return services.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate(db, data.email, data.password)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = services.authenticate(db, form.username, form.password)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)):
    return None  # nothing to do on the server side, the client just discards the token

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/verify-email", response_model=UserOut)
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    return services.verify_email(db, data.token)


@router.post("/resend-verification", response_model=Message)
def resend_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.is_verified:
        services.send_verification_email(db, user)
        db.commit()
    return Message(detail="Verification email sent")


@router.post("/forgot-password", response_model=Message)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    services.forgot_password(db, data.email)
    return Message(detail="If the email is registered, a reset link has been sent")


@router.post("/reset-password", response_model=Message)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    services.reset_password(db, data.token, data.new_password)
    return Message(detail="Password updated")
