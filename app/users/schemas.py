from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, SecretStr, AwareDatetime
from models import UserRole

class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    hashed_password: SecretStr = Field(..., max_length=255)
    role: UserRole = Field(default_factory=UserRole.ATTENDEE)
    is_verified: bool = Field(default_factory=False)
    is_active: bool = Field(default_factory=True)
    created_at: AwareDatetime = Field(default_factory=datetime.now(timezone(timedelta(hours=5))))
