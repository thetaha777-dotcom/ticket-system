from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, PositiveInt
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
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str]
    category: str = Field(..., min_length=1, max_length=255)
    images: list # im not sure if this is right
    venue: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=255)
    start_at: datetime # maybe change all datetimes to AwareDateTime where timezone is necessary
    end_at: datetime
    registration_open_at: Optional[datetime]
    registration_close_at: Optional[datetime]
    capacity: Optional[PositiveInt]
    visibility: EventVisibility
    status: EventStatus

class EventCreate(Event):
    pass

class EventUpdate(BaseModel): # should they be equal to none here?
    title:  Optional[str] = Field(..., min_length=1, max_length=255) 
    description: Optional[str]
    category:  Optional[str] = Field(..., min_length=1, max_length=255)
    images:  Optional[list] # im not sure if this is right
    venue:  Optional[str] = Field(..., min_length=1, max_length=255)
    address:  Optional[str] = Field(..., min_length=1, max_length=255)
    city:  Optional[str] = Field(..., min_length=1, max_length=255)
    start_at:  Optional[datetime] # maybe change all datetimes to AwareDateTime where timezone is necessary
    end_at:  Optional[datetime]
    registration_open_at: Optional[datetime]
    registration_close_at: Optional[datetime]
    capacity: Optional[PositiveInt]
    visibility:  Optional[EventVisibility]
    status:  Optional[EventStatus]

class EventResponse(Event):
    model_config = ConfigDict(from_attributes=True)
    
    id = int
    created_at: datetime # need to add EventClass i think