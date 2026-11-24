import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, created_at_col, enum_type, uuid_pk


class DiscountType(str, enum.Enum):
    PERCENT = "percent"   
    FIXED = "fixed"       



campaign_ticket_categories = Table(
    "promo_campaign_ticket_categories",
    Base.metadata,
    Column("campaign_id", ForeignKey("promo_campaigns.id"), primary_key=True),
    Column("ticket_category_id", ForeignKey("ticket_categories.id"), primary_key=True),
)


class PromoCampaign(Base):
    __tablename__ = "promo_campaigns"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_type: Mapped[DiscountType] = mapped_column(enum_type(DiscountType), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)   
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    max_redemptions: Mapped[int | None] = mapped_column(Integer)           
    redemption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)   
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)       
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    code: Mapped["PromoCode"] = relationship(back_populates="campaign", uselist=False, cascade="all, delete-orphan")
    ticket_categories: Mapped[list["TicketCategory"]] = relationship(secondary=campaign_ticket_categories)  # noqa: F821


class PromoCode(Base):

    __tablename__ = "promo_codes"
    __table_args__ = (UniqueConstraint("event_id", "code", name="uq_promo_event_code"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("promo_campaigns.id"), unique=True, nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    campaign: Mapped[PromoCampaign] = relationship(back_populates="code")


class PromoRedemption(Base):

    __tablename__ = "promo_redemptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("promo_campaigns.id"), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="reserved", nullable=False)   
    created_at: Mapped[datetime] = created_at_col()
