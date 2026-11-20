import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy import Session

from app.auth.schemas import RegisterRequest

from app.users.models import User, UserRole

from app.core.config import settings

from app.core.security import hash_password, create_token, decode_token

from app.shared.exceptions import ConflictError, IntegrityError
from app.shared.notifications import send_email

def register_user(db: Session, data: RegisterRequest) -> User:
    ''' Create attendee user and send verification email.

    if email already has veen registered raise exception
    
    '''

    email = format_email(data.email)

    if get_user_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.", code="email_taken")

    user = User(
        name = data.name.strip(),
        email = email,
        hashed_password = hash_password(data.password),
        role = UserRole.ATTENDEE, # we need to make a selection of roles
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # checks if another acount with same email is existing in database
        db.rollback()
        raise ConflictError("An account with this email already exists.", code="email_taken")
    db.refresh(user)

    _send_verification_email(user)
    return user


def format_email(email: str) -> str:
    return email.lower().strip()

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == format_email(email)))

def _send_verification_email(user: User) -> None:
    token = create_token(str(user.id), "verify_email", settings.email_verification_expire_mins)
    link = f"{settings.frontend_url}/verify-email?token={token}"
    send_email(user.email, "Confirm your email", f"Open this link to verify your email: {link}")