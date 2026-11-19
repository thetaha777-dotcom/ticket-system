from uuid import UUID, uuid4
from AwareDatetime import AwareDatetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PositiveInt
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

class EventCreate(Event):
    pass

class EventUpdate(BaseModel): # should they be equal to none here?
    id: Optional[UUID] = Field(default_factory=uuid4)

    title:  Optional[str] = Field(..., min_length=1, max_length=255) 
    description: Optional[str]
    category:  Optional[str] = Field(..., min_length=1, max_length=255)
    images:  Optional[HttpUrl] = Field(default_factory=list)
    venue:  Optional[str] = Field(..., min_length=1, max_length=255)
    address:  Optional[str] = Field(..., min_length=1, max_length=255)
    city:  Optional[str] = Field(..., min_length=1, max_length=255)
    start_at:  Optional[AwareDatetime]
    end_at:  Optional[AwareDatetime]
    registration_open_at: Optional[AwareDatetime]
    registration_close_at: Optional[AwareDatetime]
    capacity: Optional[PositiveInt]
    visibility:  Optional[EventVisibility]
    status:  Optional[EventStatus]

class EventResponse(Event):
    model_config = ConfigDict(from_attributes=True)
    
    created_at: AwareDatetime # need to add EventClass i think