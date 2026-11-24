import enum
import uuid
from datetime import datetime
from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, UTCDateTime, created_at_col, enum_type, utcnow, uuid_pk


class Seating(str, enum.Enum):
    GENERAL_ADMISSION = "general_admission"
    ASSIGNED_SEATING = "assigned_seating"


class EventClass(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    CANCELLED = "cancelled"


class EventVisibility(str, enum.Enum):
    PUBLIC = "public"       # listed in search
    UNLISTED = "unlisted"   # not listed, anyone with the link can open it
    PRIVATE = "private"     # link must also carry the event's access key


class RefundPolicy(str, enum.Enum):
    NONE = "none"                   # no refunds (still refunded automatically if the event is cancelled)
    BEFORE_EVENT = "before_event"
    ANYTIME = "anytime"


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"                   # temporarily reserved by a checkout in progress
    SOLD = "sold"
    UNAVAILABLE = "unavailable"     # blocked by the organizer


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    organizer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Almaty", nullable=False)
    start_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    registration_open_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    registration_close_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    capacity: Mapped[int | None] = mapped_column(Integer)
    visibility: Mapped[EventVisibility] = mapped_column(enum_type(EventVisibility), default=EventVisibility.PUBLIC, nullable=False)
    status: Mapped[EventStatus] = mapped_column(enum_type(EventStatus), default=EventStatus.DRAFT, nullable=False, index=True)
    seating: Mapped[Seating] = mapped_column(enum_type(Seating), default=Seating.GENERAL_ADMISSION, nullable=False)
    access_key: Mapped[str] = mapped_column(String(32), nullable=False)
    refund_policy: Mapped[RefundPolicy] = mapped_column(enum_type(RefundPolicy), default=RefundPolicy.BEFORE_EVENT, nullable=False)
    refund_policy_text: Mapped[str | None] = mapped_column(Text)

    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)   # set by a Platform Admin
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)   # calendar revision; grows when date/venue change
    duplicated_from_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"))

    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)

    venue: Mapped["Venue"] = relationship()  # noqa: F821
    organizer: Mapped["User"] = relationship()  # noqa: F821
    ticket_categories: Mapped[list["TicketCategory"]] = relationship(  # noqa: F821
        back_populates="event", order_by="TicketCategory.sort_order", cascade="all, delete-orphan"
    )

    @property
    def event_class(self) -> EventClass:
        now = utcnow()
        if self.status == EventStatus.CANCELLED:
            return EventClass.CANCELLED
        if now < self.start_at:
            return EventClass.UPCOMING
        if now <= self.end_at:
            return EventClass.ACTIVE
        return EventClass.COMPLETED

    @property
    def price_from(self) -> int | None:
        prices = [c.price for c in self.ticket_categories if not c.hidden]
        return min(prices) if prices else None

    @property
    def organizer_name(self) -> str:
        profile = self.organizer.organizer_profile
        return profile.display_name if profile else self.organizer.name

    @property
    def organizer_contact_email(self) -> str | None:
        profile = self.organizer.organizer_profile
        return profile.contact_email if profile else None

    @property
    def is_on_sale(self) -> bool:
        now = utcnow()
        if self.status != EventStatus.PUBLISHED or self.is_suspended:
            return False
        if self.registration_open_at and now < self.registration_open_at:
            return False
        return now < (self.registration_close_at or self.end_at)


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_staff_event_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    can_undo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class EventSeat(Base):
    __tablename__ = "event_seats"
    __table_args__ = (UniqueConstraint("event_id", "seat_id", name="uq_event_seat"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    seat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seats.id"), nullable=False)
    ticket_category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ticket_categories.id"))
    status: Mapped[SeatStatus] = mapped_column(enum_type(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False)
    held_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))

    seat: Mapped["Seat"] = relationship()  # noqa: F821


class EventReport(Base):
    __tablename__ = "event_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)   # open | reviewed | dismissed
    resolution_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at_col()

    event: Mapped[Event] = relationship()
    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])  # noqa: F821
