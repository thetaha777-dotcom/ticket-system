import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, utcnow, uuid_pk


class CaseKind(str, enum.Enum):
    ATTENDEE = "attendee"     
    ORGANIZER = "organizer"    


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"


class CaseCategory(str, enum.Enum):
    TICKET_DELIVERY = "ticket_delivery"
    PAYMENT = "payment"
    REFUND = "refund"
    SEATING = "seating"
    EVENT_INFORMATION = "event_information"
    CHECK_IN = "check_in"
    ACCOUNT = "account"
    ACTIVATION = "activation"
    TECHNICAL = "technical"


class SupportCase(Base):
    __tablename__ = "support_cases"

    id: Mapped[uuid.UUID] = uuid_pk()
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    kind: Mapped[CaseKind] = mapped_column(enum_type(CaseKind), nullable=False)
    category: Mapped[CaseCategory] = mapped_column(enum_type(CaseCategory), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(enum_type(CaseStatus), default=CaseStatus.OPEN, nullable=False, index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)   
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    messages: Mapped[list["SupportMessage"]] = relationship(
        back_populates="case", order_by="SupportMessage.created_at", cascade="all, delete-orphan"
    )
    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])  
    assigned_to: Mapped["User | None"] = relationship(foreign_keys=[assigned_to_id])  
    event: Mapped["Event | None"] = relationship()  
    order: Mapped["Order | None"] = relationship()  
    ticket: Mapped["Ticket | None"] = relationship() 


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support_cases.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    case: Mapped[SupportCase] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship()  
