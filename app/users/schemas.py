import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.users.models import UserRole, VerificationStatus



class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    is_verified: bool
    is_active: bool
    locale: str
    created_at: datetime


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr

class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    locale: str | None = Field(None, pattern="^(kk|ru|en)$")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class PayoutAccountIn(BaseModel):
    bank_name: str = Field(min_length=1, max_length=255)
    account_holder: str = Field(min_length=1, max_length=255)
    account_number: str = Field(min_length=4, max_length=34, description="Demo value. Only the last 4 characters are stored.")


class PayoutAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_name: str
    account_holder: str
    account_last4: str
    status: str
    is_simulation: bool


class OrganizerProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    contact_phone: str | None = Field(None, max_length=50)
    description: str | None = None
    website: str | None = Field(None, max_length=255)


class OrganizerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    contact_email: EmailStr
    contact_phone: str | None
    description: str | None
    website: str | None
    verification_status: VerificationStatus
    verified_at: datetime | None
    payout_account: PayoutAccountOut | None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str
    link: str | None
    is_read: bool
    created_at: datetime
