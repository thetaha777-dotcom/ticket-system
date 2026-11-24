import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, uuid_pk


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"        # checkout abandoned, reservation released


class PaymentKind(str, enum.Enum):
    TICKET_PURCHASE = "ticket_purchase"
    ACTIVATION_FEE = "activation_fee"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = uuid_pk()
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(enum_type(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)          # ticket prices before discount
    discount_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)             # what the attendee pays
    processing_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)    # deducted from the organizer payout
    currency: Mapped[str] = mapped_column(String(3), default="KZT", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_phone: Mapped[str | None] = mapped_column(String(50))
    attendees: Mapped[str | None] = mapped_column(Text)
    promo_campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("promo_campaigns.id"), index=True)
    promo_code: Mapped[str | None] = mapped_column(String(40))
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_col()
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        back_populates="order", order_by="(Ticket.seat_section, Ticket.seat_row, Ticket.seat_number, Ticket.code)"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", order_by="Payment.created_at")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="order")
    event: Mapped["Event"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    ticket_category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_categories.id"), nullable=False)
    event_seat_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("event_seats.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seat_section: Mapped[str | None] = mapped_column(String(100))
    seat_row: Mapped[str | None] = mapped_column(String(10))
    seat_number: Mapped[int | None] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")

    @property
    def line_total(self) -> int:
        return self.unit_price * self.quantity - self.discount


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[PaymentKind] = mapped_column(enum_type(PaymentKind), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    activation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paid_sales_activations.id"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KZT", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(enum_type(PaymentStatus), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="simulation", nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = created_at_col()

    order: Mapped[Order | None] = relationship(back_populates="payments")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"))
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    initiated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    order: Mapped[Order] = relationship(back_populates="refunds")
