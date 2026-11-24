import uuid
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.config import settings
from app.events.models import EventClass, EventStatus, EventVisibility, RefundPolicy, Seating, SeatStatus
from app.tickets.schemas import TicketTypeOut, TicketTypePublic
from app.users.schemas import UserBrief
from app.venues.schemas import VenueOut


def _check_timezone(value: str | None) -> str | None:
    if value is not None:
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError("Unknown time zone, use an IANA name such as Asia/Almaty") from exc
    return value


def _public_media_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.path.startswith("/media/") and parsed.hostname in (None, "localhost", "127.0.0.1", "::1"):
        url = f"{settings.api_public_url.rstrip('/')}{parsed.path}"
        if parsed.query:
            url += f"?{parsed.query}"
        if parsed.fragment:
            url += f"#{parsed.fragment}"
        return url
    return value


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(min_length=1, max_length=255)
    images: list[str] = Field(default_factory=list, max_length=8)
    venue_id: uuid.UUID
    timezone: str = "Asia/Almaty"
    start_at: datetime
    end_at: datetime
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    capacity: int | None = Field(None, ge=1)
    visibility: EventVisibility = EventVisibility.PUBLIC
    seating: Seating = Seating.GENERAL_ADMISSION
    refund_policy: RefundPolicy = RefundPolicy.BEFORE_EVENT
    refund_policy_text: str | None = None

    _tz = field_validator("timezone")(_check_timezone)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_at <= self.start_at:
            raise ValueError("The event must end after it starts")
        if self.registration_open_at and self.registration_close_at and self.registration_close_at <= self.registration_open_at:
            raise ValueError("Registration must close after it opens")
        return self


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, min_length=1, max_length=255)
    images: list[str] | None = Field(None, max_length=8)
    venue_id: uuid.UUID | None = None
    timezone: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    capacity: int | None = Field(None, ge=1)
    visibility: EventVisibility | None = None
    seating: Seating | None = None
    refund_policy: RefundPolicy | None = None
    refund_policy_text: str | None = None

    _tz = field_validator("timezone")(_check_timezone)


class EventCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("images", mode="before")
    @classmethod
    def resolve_local_media_urls(cls, value: object) -> object:
        if isinstance(value, list):
            return [_public_media_url(image) if isinstance(image, str) else image for image in value]
        return value

    id: uuid.UUID
    slug: str
    title: str
    category: str
    images: list[str]
    timezone: str
    start_at: datetime
    end_at: datetime
    status: EventStatus
    visibility: EventVisibility
    seating: Seating
    event_class: EventClass
    is_suspended: bool
    is_on_sale: bool
    price_from: int | None
    organizer_name: str
    venue: VenueOut


class EventPage(BaseModel):
    items: list[EventCard]
    total: int


class EventDetail(EventCard):
    description: str | None
    registration_open_at: datetime | None
    registration_close_at: datetime | None
    capacity: int | None
    refund_policy: RefundPolicy
    refund_policy_text: str | None
    organizer_contact_email: str | None
    paid_sales_active: bool = False
    can_manage: bool = False
    ticket_types: list[TicketTypePublic] = []


class EventStats(BaseModel):
    capacity: int
    tickets_sold: int
    tickets_reserved: int
    checked_in: int
    orders: int
    gross_sales: int


class EventManage(EventCard):
    organizer_id: uuid.UUID
    description: str | None
    registration_open_at: datetime | None
    registration_close_at: datetime | None
    capacity: int | None
    refund_policy: RefundPolicy
    refund_policy_text: str | None
    access_key: str
    suspended_reason: str | None
    duplicated_from_id: uuid.UUID | None
    published_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    paid_sales_active: bool = False
    ticket_types: list[TicketTypeOut] = []
    stats: EventStats | None = None


class CancelEventIn(BaseModel):
    reason: str | None = Field(None, max_length=500)


class StaffIn(BaseModel):
    email: EmailStr
    can_undo: bool = True


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user: UserBrief
    can_undo: bool
    created_at: datetime


class EventReportIn(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


# --- seating ---


class SeatingSectionIn(BaseModel):
    section_id: uuid.UUID
    ticket_category_id: uuid.UUID | None = Field(None, description="Ticket type sold in this section; null = section closed")


class SeatingConfigIn(BaseModel):
    sections: list[SeatingSectionIn]
    unavailable_seat_ids: list[uuid.UUID] = Field(default_factory=list, description="Venue seat ids blocked for this event")


class SeatMapSeat(BaseModel):
    id: uuid.UUID            # event-seat id: what checkout sends back
    seat_id: uuid.UUID       # venue seat id
    number: int
    is_accessible: bool
    status: SeatStatus
    held_by_me: bool = False


class SeatMapRow(BaseModel):
    label: str
    seats: list[SeatMapSeat]


class SeatMapSection(BaseModel):
    id: uuid.UUID
    name: str
    price_category: str
    ticket_category_id: uuid.UUID | None
    ticket_type_name: str | None
    price: int | None
    rows: list[SeatMapRow]


class SeatMapOut(BaseModel):
    event_id: uuid.UUID
    configured: bool
    sections: list[SeatMapSection]


class CalendarLinks(BaseModel):
    ics: str
    google: str
    outlook: str
    office365: str
    yahoo: str
