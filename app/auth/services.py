import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.schemas import RegisterRequest
from app.core.config import settings
from app.core.security import (
    create_token,
    decode_token,
    get_password_hash,
    password_fingerprint,
    verify_password,
)
from app.notifications.services import notify
from app.shared.exceptions import AppError, Conflict, Forbidden, Unauthorized
from app.users.models import OrganizerProfile, User, UserRole


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def send_verification_email(db: Session, user: User) -> None:
    token = create_token(str(user.id), "verify_email", settings.email_verification_expire_mins)
    notify(
        db, user, "account_verification", "Confirm your BiletFlow email address",
        f"Hello {user.name},\nPlease confirm your email address to finish setting up your account.",
        link=f"/verify-email?token={token}", in_app=False,
    )


def register(db: Session, data: RegisterRequest) -> User:
    if get_user_by_email(db, data.email):
        raise Conflict("An account with this email already exists", "email_taken")
    user = User(
        name=data.name.strip(),
        email=data.email.strip().lower(),
        hashed_password=get_password_hash(data.password),
        role=UserRole(data.role),
        locale=data.locale,
    )
    db.add(user)
    db.flush()   # gives the user an id without ending the transaction
    if user.role == UserRole.ORGANIZER:
        db.add(OrganizerProfile(user_id=user.id, display_name=user.name, contact_email=user.email))
    send_verification_email(db, user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise Unauthorized("Incorrect email or password", "invalid_credentials")
    if not user.is_active:
        raise Forbidden("This account has been suspended", "account_suspended")
    return user


def verify_email(db: Session, token: str) -> User:
    payload = decode_token(token, "verify_email")
    user = db.get(User, uuid.UUID(payload["sub"])) if payload else None
    if user is None:
        raise AppError("The verification link is invalid or has expired", "invalid_token")
    user.is_verified = True
    db.commit()
    return user


def forgot_password(db: Session, email: str) -> None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    token = create_token(
        str(user.id), "reset_password", settings.password_reset_expire_mins,
        extra={"fp": password_fingerprint(user.hashed_password)},
    )
    notify(
        db, user, "password_reset", "Reset your BiletFlow password",
        f"Hello {user.name},\nUse the link below to choose a new password. "
        f"It works once and expires in {settings.password_reset_expire_mins} minutes.\n"
        "If you did not ask for this, you can ignore this email.",
        link=f"/reset-password?token={token}", in_app=False,
    )
    db.commit()


def reset_password(db: Session, token: str, new_password: str) -> None:
    payload = decode_token(token, "reset_password")
    user = db.get(User, uuid.UUID(payload["sub"])) if payload else None
    # The fingerprint changes as soon as the password changes, so a used link stops working.
    if user is None or payload.get("fp") != password_fingerprint(user.hashed_password):
        raise AppError("The reset link is invalid or has expired", "invalid_token")
    user.hashed_password = get_password_hash(new_password)
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AppError("The current password is not correct", "invalid_credentials")
    user.hashed_password = get_password_hash(new_password)
    db.commit()
