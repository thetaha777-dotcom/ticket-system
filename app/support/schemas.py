import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.support.models import CaseCategory, CaseKind, CaseStatus
from app.users.schemas import UserBrief


class CaseCreate(BaseModel):
    kind: CaseKind = Field(CaseKind.ATTENDEE, description="attendee = to the event organizer, organizer = to platform support")
    category: CaseCategory
    subject: str = Field(min_length=3, max_length=255)
    message: str = Field(min_length=1, max_length=5000)
    event_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    ticket_id: uuid.UUID | None = None


class CaseUpdate(BaseModel):
    status: CaseStatus | None = None
    assigned_to_id: uuid.UUID | None = None
    is_escalated: bool | None = None


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class MessageOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    from_staff: bool      
    body: str
    created_at: datetime


class CaseContext(BaseModel):
    event_id: uuid.UUID | None = None
    event_title: str | None = None
    event_slug: str | None = None
    order_id: uuid.UUID | None = None
    order_number: str | None = None
    ticket_id: uuid.UUID | None = None
    ticket_code: str | None = None


class CaseOut(BaseModel):
    id: uuid.UUID
    number: str
    kind: CaseKind
    category: CaseCategory
    subject: str
    status: CaseStatus
    is_escalated: bool
    requester: UserBrief
    assigned_to: UserBrief | None
    context: CaseContext
    created_at: datetime
    updated_at: datetime
    message_count: int
    can_manage: bool      


class CaseDetail(CaseOut):
    messages: list[MessageOut]
