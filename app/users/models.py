import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, uuid_pk


class UserRole(str, enum.Enum):
    ATTENDEE = "attendee"
    ORGANIZER = "organizer"
    EVENT_ADMIN = "event_admin"
    PLATFORM_ADMIN = "platform_admin"


class VerificationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    VERIFIED = "verified"



class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole), default=UserRole.ATTENDEE, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)        #languages!
    created_at: Mapped[datetime] = created_at_col()

    organizer_profile: Mapped["OrganizerProfile | None"] = relationship(back_populates="user", uselist=False)



class OrganizerProfile(Base):
    __tablename__ = "organizer_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        enum_type(VerificationStatus), default=VerificationStatus.NOT_STARTED, nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship(back_populates="organizer_profile")
    payout_account: Mapped["PayoutAccount | None"] = relationship(back_populates="profile", uselist=False)


class PayoutAccount(Base):
    __tablename__ = "payout_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    organizer_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizer_profiles.id"), unique=True, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_holder: Mapped[str] = mapped_column(String(255), nullable=False)
    account_last4: Mapped[str] = mapped_column(String(4), nullable=False)   # only the last 4 characters are kept
    status: Mapped[str] = mapped_column(String(32), default="verified", nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    profile: Mapped[OrganizerProfile] = relationship(back_populates="payout_account")
