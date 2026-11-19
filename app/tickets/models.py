from app.core.database import Base
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

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
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id:Mapped[uuid.UUID] = mapped_column(ForeignKey('events.id'), nullable=False)
    type:Mapped[enum.Enum] = mapped_column(Enum(TicketType), nullable=False)
    name:Mapped[String] = mapped_column(String(255), nullable=False)
    description:Mapped[String] = mapped_column(Text, nullable=False)
    price:Mapped[float] = mapped_column(Float, nullable=True)
    order_limit:Mapped[int] = mapped_column(Integer, nullable=False)
    quantity:Mapped[int] = mapped_column(Integer, nullable=False)
    available:Mapped[int] = mapped_column(Integer, nullable=False, default = 0)
    reserved:Mapped[int] = mapped_column(Integer, nullable=False, default = 0)
    sold:Mapped[int] = mapped_column(Integer, nullable=False, default = 0)
    refunded:Mapped[int] = mapped_column(Integer, nullable=False, default = 0)
    checked_in:Mapped[int] = mapped_column(Integer, nullable=False, default = 0)
    hidden:Mapped[bool] = mapped_column(Boolean, nullable=False, default = False)
    sale_start:Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sale_end:Mapped[datetime] = mapped_column(DateTime, nullable=False)



class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ticket_category_id:Mapped[uuid.UUID] = mapped_column(ForeignKey('tickets.id'), nullable=False)
    order_id:Mapped[uuid.UUID] = mapped_column(ForeignKey('orders.id'), nullable=False)
    seat_section: Mapped[int] = mapped_column(Integer, nullable=True)
    seat_row: Mapped[int] = mapped_column(Integer, nullable=True)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[enum.Enum] = mapped_column(Enum(TicketStatus), nullable=False, default=TicketStatus.VALID)
