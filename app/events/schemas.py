from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, PositiveInt, AwareDatetime
from typing import Optional


class EventClass(str, Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EventVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"

class EventStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    CANCELLED = "cancelled"

class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str]
    category: str = Field(..., min_length=1, max_length=255)
    images: list[HttpUrl] = Field(default_factory=list)
    venue: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=255)
    start_at: AwareDatetime
    end_at: AwareDatetime
    registration_open_at: Optional[AwareDatetime]
    registration_close_at: Optional[AwareDatetime]
    capacity: Optional[PositiveInt]
    visibility: EventVisibility
    status: EventStatus
    class Config:
            from_attributes = True