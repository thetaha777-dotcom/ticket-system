import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.promos.models import DiscountType


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    discount_type: DiscountType
    discount_value: int = Field(ge=1, description="Percent (1-100) or whole KZT per ticket")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_redemptions: int | None = Field(None, ge=1, description="Maximum number of orders; empty = unlimited")
    ticket_category_ids: list[uuid.UUID] = Field(default_factory=list, description="Empty = all ticket types")
    code: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{3,40}$", description="Leave empty to generate one")

    @model_validator(mode="after")
    def check(self):
        if self.discount_type == DiscountType.PERCENT and self.discount_value > 100:
            raise ValueError("A percentage discount cannot be more than 100")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("The campaign must end after it starts")
        return self


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    ends_at: datetime | None = None
    max_redemptions: int | None = Field(None, ge=1)


class CampaignStats(BaseModel):

    redemptions: int
    orders: int
    tickets_sold: int
    gross_revenue: int
    discount_amount: int
    net_revenue: int
    link_visits: int


class CampaignOut(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    code: str
    link: str                
    discount_type: DiscountType
    discount_value: int
    starts_at: datetime | None
    ends_at: datetime | None
    max_redemptions: int | None
    is_active: bool
    ticket_category_ids: list[uuid.UUID]
    created_at: datetime
    stats: CampaignStats


class PromoPreview(BaseModel):

    event_id: uuid.UUID
    event_slug: str
    code: str
    campaign_name: str
    discount_type: DiscountType
    discount_value: int
    ticket_category_ids: list[uuid.UUID]   


class PromoCheckIn(BaseModel):
    event_id: uuid.UUID
    code: str = Field(min_length=1, max_length=40)
