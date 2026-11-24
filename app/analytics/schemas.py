import uuid
from datetime import date, datetime

from pydantic import BaseModel


class CapacityBlock(BaseModel):
    total: int
    sold: int
    remaining: int
    percent_sold: float


class RevenueBlock(BaseModel):
    
    gross: int        # ticket prices before discounts, including orders refunded later
    discounts: int
    refunds: int
    net: int          # gross - discounts - refunds


class SalesPoint(BaseModel):
    date: date        # in the event's time zone
    orders: int
    tickets: int
    revenue: int


class TicketTypeRow(BaseModel):
    ticket_type_id: uuid.UUID
    name: str
    price: int
    quantity: int
    sold: int
    remaining: int
    revenue: int
    checked_in: int


class CampaignRow(BaseModel):
    campaign_id: uuid.UUID
    name: str
    code: str
    is_active: bool
    redemptions: int
    tickets: int
    gross: int
    discount: int
    net: int


class AttendanceBlock(BaseModel):
    registered: int
    checked_in: int
    absent: int
    percent: float


class EventAnalytics(BaseModel):
    event_id: uuid.UUID
    generated_at: datetime
    currency: str = "KZT"
    is_simulation: bool = True
    capacity: CapacityBlock
    revenue: RevenueBlock
    sales_over_time: list[SalesPoint]
    by_ticket_type: list[TicketTypeRow]
    campaigns: list[CampaignRow]
    attendance: AttendanceBlock


class OrganizerSummary(BaseModel):
    events: int
    upcoming_events: int
    tickets_sold: int
    net_revenue: int
    checked_in: int
