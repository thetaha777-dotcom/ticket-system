from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import AwareDatetime, BaseModel, Field, NonNegativeFloat, NonNegativeInt
from models import TicketType, TicketStatus

class TicketCategory(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_id: UUID = Field(default_factory=uuid4)
    type: TicketType
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    price: Optional[NonNegativeFloat]
    order_limit: NonNegativeInt
    quantity: NonNegativeInt
    available: NonNegativeInt = Field(default_factory=0)
    reserved: NonNegativeInt = Field(default_factory=0)
    sold: NonNegativeInt = Field(default_factory=0)
    refunded: NonNegativeInt = Field(default_factory=0)
    checked_in: NonNegativeInt = Field(default_factory=0)
    hidden: bool = Field(default_factory=False)
    sale_start: AwareDatetime
    sale_end: AwareDatetime
    class Config:
        from_attributes = True

class Ticket(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ticket_category_id: UUID = Field(default_factory=uuid4)
    order_id: UUID = Field(default_factory=uuid4)
    seat_section: Optional[NonNegativeInt]
    seat_row: Optional[NonNegativeInt]
    seat_number: Optional[NonNegativeInt]
    status: TicketStatus = Field(default_factory=TicketStatus.VALID)
    class Config:
        from_attributes = True
