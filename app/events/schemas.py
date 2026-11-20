from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, PositiveInt, AwareDatetime
from typing import Optional

from models import Seating, EventClass, EventStatus, EventVisibility

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
    visibility: EventVisibility = Field(default_factory=EventVisibility.PUBLIC)
    status: EventStatus = Field(default_factory=EventStatus.DRAFT)
    seating: Seating = Field(default_factory=Seating.GENERAL_ADMISSION)
    event_class: EventClass = Field(default_factory=EventClass.UPCOMING)
    class Config:
            from_attributes = True