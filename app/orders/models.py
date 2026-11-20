from app.core.database import Base
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    order_total: Mapped[int] = mapped_column(Integer, nullable=True)
    order_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class OrderTicket(Base):
    __tablename__ = "ordertickets"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id"), nullable=False)