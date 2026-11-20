from typing import Optional
from pydantic import BaseModel, Field, NonNegativeInt
import uuid

class Venue(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(..., max_length=255)
    city: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=255)
    sections: Optional[NonNegativeInt]
    rows: Optional[NonNegativeInt]
    cols: Optional[NonNegativeInt]

class VenuesEvents(BaseModel):
    venue_id: uuid.UUID
    event_id: uuid.UUID
    fill_line: str = Field(..., min_length=1, max_length=10000)
