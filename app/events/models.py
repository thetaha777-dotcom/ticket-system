from app.core.database import Base
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class Seating(str, enum.Enum):
    GENERAL_ADMISSION = "general_admission"
    ASSIGNED_SEATING = "assigned_seating"

class EventClass(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
class EventStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    CANCELLED = "cancelled"

class EventVisibility(str, enum.Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


    
class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    images: Mapped[list] = mapped_column(JSON, default=list)
    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visibility: Mapped[EventVisibility] = mapped_column(Enum(EventVisibility), default=EventVisibility.PUBLIC, nullable=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    seating: Mapped[enum.Enum] = mapped_column(Enum(Seating), nullable=False, default=Seating.GENERAL_ADMISSION)
    event_class: Mapped[enum.Enum] = mapped_column(Enum(EventClass), nullable=False, default=EventClass.UPCOMING)