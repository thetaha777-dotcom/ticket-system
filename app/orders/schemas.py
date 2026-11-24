import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.orders.models import OrderStatus, PaymentKind, PaymentStatus
from app.promos.models import DiscountType
from app.tickets.schemas import EventBrief, TicketOut


class OrderLineIn(BaseModel):
    ticket_category_id: uuid.UUID
    quantity: int = Field(ge=1, le=50)


class AttendeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None


class OrderCreate(BaseModel):
    event_id: uuid.UUID
    items: list[OrderLineIn] = Field(default_factory=list)
    seat_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20, description="Event-seat ids from the seat map")
    promo_code: str | None = Field(None, max_length=40)
    buyer_name: str | None = Field(None, max_length=255)
    buyer_email: EmailStr | None = None
    buyer_phone: str | None = Field(None, max_length=50)
    attendees: list[AttendeeIn] = Field(default_factory=list, description="Optional name per ticket, in order")


class QuoteLine(BaseModel):
    ticket_category_id: uuid.UUID
    event_seat_id: uuid.UUID | None = None
    name: str
    quantity: int
    unit_price: int
    discount: int
    line_total: int
    seat_section: str | None = None
    seat_row: str | None = None
    seat_number: int | None = None


class AppliedPromo(BaseModel):
    code: str
    campaign_name: str
    discount_type: DiscountType
    discount_value: int


class QuoteOut(BaseModel):
    lines: list[QuoteLine]
    quantity: int
    subtotal: int
    discount_total: int
    total: int
    currency: str = "KZT"
    promo: AppliedPromo | None = None


class PayIn(BaseModel):
    outcome: Literal["success", "failure"] = Field("success", description="Result the payment simulator should produce")


class ReasonIn(BaseModel):
    reason: str | None = Field(None, max_length=500)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_category_id: uuid.UUID
    name: str
    quantity: int
    unit_price: int
    discount: int
    line_total: int
    seat_section: str | None
    seat_row: str | None
    seat_number: int | None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: PaymentKind
    order_id: uuid.UUID | None
    event_id: uuid.UUID | None
    amount: int
    processing_fee: int
    currency: str
    status: PaymentStatus
    provider: str
    provider_reference: str
    is_simulation: bool
    failure_reason: str | None
    created_at: datetime


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    amount: int
    reason: str | None
    status: str
    is_simulation: bool
    created_at: datetime


class OrderOut(BaseModel):
    id: uuid.UUID
    number: str
    status: OrderStatus
    event: EventBrief
    quantity: int
    subtotal: int
    discount_total: int
    total: int
    processing_fee: int | None
    currency: str
    buyer_name: str
    buyer_email: str
    buyer_phone: str | None
    promo_code: str | None
    expires_at: datetime | None
    created_at: datetime
    paid_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    refund_eligible: bool
    is_simulation: bool = True
    items: list[OrderItemOut]
    tickets: list[TicketOut]
    payments: list[PaymentOut]
    refunds: list[RefundOut]


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int


class AttendeeRow(BaseModel):
    ticket_id: uuid.UUID
    code: str
    status: str
    attendee_name: str
    attendee_email: str
    ticket_type: str
    seat: str | None
    order_id: uuid.UUID
    order_number: str
    issued_at: datetime
    checked_in_at: datetime | None


class SalesSummary(BaseModel):
    gross_sales: int
    discounts: int
    refunds: int
    processing_fees: int
    net_revenue: int        # gross - discounts - refunds
    estimated_payout: int   # net revenue - processing fees
    orders: int
    refunded_orders: int
    is_simulation: bool = True
