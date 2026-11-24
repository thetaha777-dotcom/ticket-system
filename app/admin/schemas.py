import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.activation.models import ActivationStatus
from app.orders.models import OrderStatus
from app.users.models import UserRole
from app.users.schemas import UserBrief, UserOut


class Overview(BaseModel):
    users: int
    organizers: int
    events_published: int
    events_suspended: int
    orders_completed: int
    tickets_issued: int
    gross_sales: int             # demonstration KZT
    refunds_total: int
    payment_failures: int
    activations_active: int
    activations_suspended: int
    open_reports: int
    open_support_cases: int


class UserPage(BaseModel):
    items: list[UserOut]
    total: int


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class SuspendEventIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AdminEventRow(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    status: str
    visibility: str
    is_suspended: bool
    suspended_reason: str | None
    start_at: datetime
    organizer: UserBrief
    tickets_sold: int
    open_reports: int


class AdminEventPage(BaseModel):
    items: list[AdminEventRow]
    total: int


class AdminOrderRow(BaseModel):
    id: uuid.UUID
    number: str
    status: OrderStatus
    total: int
    quantity: int
    buyer_name: str
    buyer_email: str
    event_id: uuid.UUID
    event_title: str
    promo_code: str | None
    created_at: datetime


class AdminOrderPage(BaseModel):
    items: list[AdminOrderRow]
    total: int


class ActivationRow(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    event_title: str
    organizer: UserBrief
    status: ActivationStatus
    fee_amount: int
    fee_paid: bool
    terms_accepted: bool
    activated_at: datetime | None
    suspended_reason: str | None
    created_at: datetime


class ReportRow(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    event_title: str
    event_slug: str
    event_suspended: bool
    reporter: UserBrief
    reason: str
    status: str
    resolution_note: str | None
    created_at: datetime


class ReportUpdate(BaseModel):
    status: str = Field(pattern="^(open|reviewed|dismissed)$")
    resolution_note: str | None = Field(None, max_length=1000)


class PromoActivityRow(BaseModel):
    campaign_id: uuid.UUID
    event_id: uuid.UUID
    event_title: str
    name: str
    code: str
    is_active: bool
    max_redemptions: int | None
    redemptions: int
    discount_amount: int
    net_revenue: int


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activation_fee_kzt: int
    processing_fee_percent: float
    order_hold_minutes: int


class SettingsUpdate(BaseModel):
    activation_fee_kzt: int | None = Field(None, ge=0, le=10_000_000)
    processing_fee_percent: float | None = Field(None, ge=0, le=50)
    order_hold_minutes: int | None = Field(None, ge=1, le=120)
