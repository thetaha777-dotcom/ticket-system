import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.tickets.models import TicketStatus, TicketType

MAX_PRICE = 10_000_000


class TicketTypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: TicketType
    price: int = Field(0, ge=0, le=MAX_PRICE, description="Whole tenge without tiyn, must be 0 for free tickets")
    quantity: int = Field(ge=1, le=100_000)
    order_limit: int = Field(10, ge=1, le=50, description="Maximum tickets of this type in one order")
    hidden: bool = False
    sale_start: datetime | None = None
    sale_end: datetime | None = None

    @model_validator(mode="after")
    def check(self):
        if self.type == TicketType.FREE:
            self.price = 0
        elif self.price <= 0:
            raise ValueError("A paid ticket type needs a price above 0")
        if self.sale_start and self.sale_end and self.sale_end <= self.sale_start:
            raise ValueError("Sales must end after they start")
        return self


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: int | None = Field(None, ge=0, le=MAX_PRICE)
    quantity: int | None = Field(None, ge=1, le=100_000)
    order_limit: int | None = Field(None, ge=1, le=50)
    hidden: bool | None = None
    sale_start: datetime | None = None
    sale_end: datetime | None = None


class TicketTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_id: uuid.UUID
    type: TicketType
    name: str
    description: str | None
    price: int
    order_limit: int
    quantity: int
    available: int
    reserved: int
    sold: int
    refunded: int
    checked_in: int
    hidden: bool
    sale_start: datetime | None
    sale_end: datetime | None


class TicketTypePublic(BaseModel):
    id: uuid.UUID
    type: TicketType
    name: str
    description: str | None
    price: int
    order_limit: int
    available: int
    sale_start: datetime | None
    sale_end: datetime | None
    on_sale: bool
    unavailable_reason: str | None


class EventBrief(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    start_at: datetime
    end_at: datetime
    timezone: str
    status: str
    image: str | None
    venue_name: str
    venue_address: str
    venue_city: str


class TicketOut(BaseModel):
    id: uuid.UUID
    code: str
    status: TicketStatus
    event_id: uuid.UUID
    order_id: uuid.UUID
    order_number: str
    ticket_type: str
    attendee_name: str
    attendee_email: str
    seat_section: str | None
    seat_row: str | None
    seat_number: int | None
    issued_at: datetime
    checked_in_at: datetime | None
    qr_payload: str | None
    event: EventBrief
