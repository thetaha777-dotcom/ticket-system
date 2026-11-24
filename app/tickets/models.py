import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, uuid_pk


class TicketStatus(str, enum.Enum):
    VALID = "valid"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class TicketType(str, enum.Enum):
    FREE = "free"
    PAID = "paid"




class TicketCategory(Base): #for example adult/child ticket
    __tablename__ = "ticket_categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    type: Mapped[TicketType] = mapped_column(enum_type(TicketType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)          # whole KZT
    order_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # max tickets of this type in one order
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)                  # total inventory
    # Counters. They are changed only with atomic "UPDATE ... WHERE" statements (see orders/services.py).
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)       # in a checkout that is not finished yet
    sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)           # issued and still valid / checked in
    refunded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checked_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sale_start: Mapped[datetime | None] = mapped_column(UTCDateTime)
    sale_end: Mapped[datetime | None] = mapped_column(UTCDateTime)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    event: Mapped["Event"] = relationship(back_populates="ticket_categories")  # noqa: F821

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved - self.sold, 0)




class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)   # human-readable ticket identifier
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    ticket_category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_categories.id"), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    event_seat_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("event_seats.id"))
    # Attendee (the SRS "Attendee" entity is stored right on the ticket)
    attendee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attendee_email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Assigned seat, copied here so the ticket stays readable even if the venue layout changes later
    seat_section: Mapped[str | None] = mapped_column(String(100))
    seat_row: Mapped[str | None] = mapped_column(String(10))
    seat_number: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[TicketStatus] = mapped_column(enum_type(TicketStatus), default=TicketStatus.VALID, nullable=False)
    issued_at: Mapped[datetime] = created_at_col()
    checked_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    category: Mapped[TicketCategory] = relationship()
    event: Mapped["Event"] = relationship()  
    order: Mapped["Order"] = relationship(back_populates="tickets") 


class CheckInRecord(Base):

    __tablename__ = "check_in_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)    # check_in | undo
    method: Mapped[str] = mapped_column(String(16), nullable=False)    # scan | manual
    created_at: Mapped[datetime] = created_at_col()

    ticket: Mapped[Ticket] = relationship()
    staff: Mapped["User"] = relationship()  # noqa: F821
