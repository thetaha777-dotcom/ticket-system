from app.core.database import Base
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, Text, JSON, Integer, ForeignKey, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Venue(Base):
    __tablename__ = "venues"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    sections: Mapped[int] = mapped_column(Integer, nullable=True)
    rows: Mapped[int] = mapped_column(Integer, nullable=True)
    cols: Mapped[int] = mapped_column(Integer, nullable=True)


class VenuesEvents(Base):
    __tablename__ = "venues_events"
    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False, primary_key=True)
    fill_line: Mapped[str] = mapped_column(String(10000), nullable=False)