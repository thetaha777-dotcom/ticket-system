import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, uuid_pk


class ActivationStatus(str, enum.Enum):
    PENDING = "pending"        
    ACTIVE = "active"          
    SUSPENDED = "suspended"    

class PaidSalesActivation(Base):
    
    __tablename__ = "paid_sales_activations"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), unique=True, nullable=False)
    organizer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ActivationStatus] = mapped_column(enum_type(ActivationStatus), default=ActivationStatus.PENDING, nullable=False)
    fee_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fee_paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    suspended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
