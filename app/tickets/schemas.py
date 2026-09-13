import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, PositiveInt


class TicketTypeCategory(str, Enum):
    FREE = "free"
    PAID = "paid"

class TicketStatus(str, Enum):
    VALID = "valid"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class TicketTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100) # need to reconsider parameters etc
    description: Optional[str]
    category: TicketTypeCategory
    price: Decimal = Field(..., ge=0.0, decimal_places=2) # temporary numbers
    quantity: PositiveInt = Field(..., ge = 1)

class TicketTypeCreate(TicketTypeBase):
    pass

class TicketTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    total_quantity: Optional[PositiveInt] = None

class TicketTypeResponse(TicketTypeBase):
    id: int
    event_id: int
    available_quantity: int
    reserved_quantity: int
    sold_quantity: int
    refunded_quantity: int
    checked_in_quantity: int
    created_at: datetime

    class Config:
        from_attributes = True
