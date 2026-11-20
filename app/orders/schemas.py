from uuid import UUID, uuid4
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, NonNegativeInt, PositiveInt
from typing import Optional


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    event_id: UUID
    order_total: Optional[NonNegativeInt]
    order_quantity: NonNegativeInt
    order_date: AwareDatetime

class OrderTicket(BaseModel):
    order_id: UUID
    ticket_id: UUID