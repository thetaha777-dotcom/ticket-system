import base64
import hashlib
import hmac
import uuid
from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.database import utcnow


_BCRYPT_ROUNDS = 4 if settings.environment == "test" else 12


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def create_token(subject: str, purpose: str, expires_mins: int, extra: dict | None = None) -> str:
    payload = {"sub": subject, "purpose": purpose, "exp": utcnow() + timedelta(minutes=expires_mins)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.algorithm)


def decode_token(token: str, purpose: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


def password_fingerprint(hashed_password: str) -> str:
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


TICKET_QR_PREFIX = "BFT1"


def _ticket_signature(ticket_id: uuid.UUID) -> str:
    digest = hmac.new(settings.SECRET_KEY.encode(), f"ticket:{ticket_id.hex}".encode(), hashlib.sha256).digest()
    return base64.b32encode(digest[:15]).decode()  # 24 chars, A-Z and 2-7


def ticket_qr_payload(ticket_id: uuid.UUID) -> str:
    return f"{TICKET_QR_PREFIX}.{ticket_id.hex.upper()}.{_ticket_signature(ticket_id)}"


def parse_ticket_qr(payload: str) -> uuid.UUID | None:
    """Return the ticket id when the payload is a genuine BiletFlow admission QR, else None."""
    parts = payload.strip().split(".")
    if len(parts) != 3 or parts[0] != TICKET_QR_PREFIX:
        return None
    try:
        ticket_id = uuid.UUID(hex=parts[1])
    except ValueError:
        return None
    if not hmac.compare_digest(parts[2], _ticket_signature(ticket_id)):
        return None
    return ticket_id
