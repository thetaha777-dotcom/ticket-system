import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ScanResultCode = Literal["valid", "already_used", "cancelled", "refunded", "invalid", "wrong_event", "campaign_qr"]


class CheckInStats(BaseModel):
    registered: int
    checked_in: int
    remaining: int


class StaffEventOut(BaseModel):
    id: uuid.UUID
    title: str
    start_at: datetime
    end_at: datetime
    timezone: str
    status: str
    event_class: str
    venue_name: str
    venue_city: str
    can_undo: bool
    stats: CheckInStats


class TicketScanInfo(BaseModel):
    id: uuid.UUID
    code: str
    status: str
    attendee_name: str
    attendee_email: str
    ticket_type: str
    seat: str | None
    order_number: str
    checked_in_at: datetime | None


class ScanIn(BaseModel):
    qr_payload: str = Field(min_length=1, max_length=2000, description="Exact text read from the QR code")
    check_in: bool = Field(True, description="False = only verify, do not record the entry")


class ScanOut(BaseModel):
    result: ScanResultCode
    message: str
    ticket: TicketScanInfo | None = None
    stats: CheckInStats


class CheckInRecordOut(BaseModel):
    id: uuid.UUID
    action: str
    method: str
    created_at: datetime
    staff_name: str
    ticket_code: str
    attendee_name: str
