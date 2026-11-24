import secrets
import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.audit.services import record
from app.core.config import settings
from app.core.database import utcnow
from app.events.models import Event
from app.orders.models import Order, OrderStatus
from app.promos.models import DiscountType, PromoCampaign, PromoCode, PromoRedemption
from app.promos.schemas import CampaignIn, CampaignOut, CampaignStats, CampaignUpdate, PromoPreview
from app.shared import qr
from app.shared.exceptions import AppError, Conflict, NotFound
from app.shared.utils import format_kzt, random_code
from app.tickets.models import TicketCategory
from app.users.models import User


def campaign_link(event: Event, campaign: PromoCampaign) -> str:
    return f"{settings.frontend_url}/e/{event.slug}?c={campaign.code.token}"


def _describe(campaign: PromoCampaign) -> str:
    if campaign.discount_type == DiscountType.PERCENT:
        return f"{campaign.discount_value}% off"
    return f"{format_kzt(campaign.discount_value)} off per ticket"


# organizer side-


def create_campaign(db: Session, event: Event, user: User, data: CampaignIn) -> PromoCampaign:
    code = (data.code or random_code(8)).upper()
    if db.scalar(select(PromoCode.id).where(PromoCode.event_id == event.id, PromoCode.code == code)):
        raise Conflict("This promo code is already used for the event", "promo_code_taken")
    categories = []
    if data.ticket_category_ids:
        categories = list(db.scalars(select(TicketCategory).where(
            TicketCategory.event_id == event.id, TicketCategory.id.in_(data.ticket_category_ids))))
        if len(categories) != len(set(data.ticket_category_ids)):
            raise AppError("Some ticket types do not belong to this event", "ticket_type_not_found")
    campaign = PromoCampaign(
        event_id=event.id, name=data.name, discount_type=data.discount_type, discount_value=data.discount_value,
        starts_at=data.starts_at, ends_at=data.ends_at, max_redemptions=data.max_redemptions, created_by_id=user.id,
        ticket_categories=categories,
        code=PromoCode(event_id=event.id, code=code, token=secrets.token_urlsafe(18)),
    )
    db.add(campaign)
    db.flush()
    record(db, actor=user, action="promo.created", entity_type="promo_campaign", entity_id=campaign.id, event_id=event.id,
           description=f"Promo campaign «{campaign.name}» created: code {code}, {_describe(campaign)}")
    db.commit()
    return campaign


def get_campaign(db: Session, event: Event, campaign_id: uuid.UUID) -> PromoCampaign:
    campaign = db.get(PromoCampaign, campaign_id)
    if campaign is None or campaign.event_id != event.id:
        raise NotFound("Campaign not found", "campaign_not_found")
    return campaign


def update_campaign(db: Session, event: Event, user: User, campaign: PromoCampaign, data: CampaignUpdate) -> PromoCampaign:
    changes = data.model_dump(exclude_unset=True)
    if "is_active" in changes and changes["is_active"] != campaign.is_active:
        action = "promo.enabled" if changes["is_active"] else "promo.disabled"
        record(db, actor=user, action=action, entity_type="promo_campaign", entity_id=campaign.id, event_id=event.id,
               description=f"Promo code {campaign.code.code} {'enabled' if changes['is_active'] else 'disabled'}")
    for field, value in changes.items():
        setattr(campaign, field, value)
    db.commit()
    return campaign


def campaign_stats(db: Session, campaign: PromoCampaign) -> CampaignStats:
    orders, tickets, gross, discount, net = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.quantity), 0), func.coalesce(func.sum(Order.subtotal), 0),
               func.coalesce(func.sum(Order.discount_total), 0), func.coalesce(func.sum(Order.total), 0))
        .where(Order.promo_campaign_id == campaign.id, Order.status == OrderStatus.COMPLETED)
    ).one()
    return CampaignStats(redemptions=campaign.redemption_count, orders=orders, tickets_sold=tickets, gross_revenue=gross,
                         discount_amount=discount, net_revenue=net, link_visits=campaign.visit_count)


def campaign_out(db: Session, event: Event, campaign: PromoCampaign) -> CampaignOut:
    return CampaignOut(
        id=campaign.id, event_id=event.id, name=campaign.name, code=campaign.code.code, link=campaign_link(event, campaign),
        discount_type=campaign.discount_type, discount_value=campaign.discount_value, starts_at=campaign.starts_at,
        ends_at=campaign.ends_at, max_redemptions=campaign.max_redemptions, is_active=campaign.is_active,
        ticket_category_ids=[c.id for c in campaign.ticket_categories], created_at=campaign.created_at,
        stats=campaign_stats(db, campaign),
    )


def list_campaigns(db: Session, event: Event) -> list[CampaignOut]:
    campaigns = db.scalars(select(PromoCampaign).where(PromoCampaign.event_id == event.id).order_by(PromoCampaign.created_at.desc()))
    return [campaign_out(db, event, c) for c in campaigns]


def campaign_qr(event: Event, campaign: PromoCampaign) -> bytes:
    return qr.campaign_qr_png(campaign_link(event, campaign), campaign.code.code)


# attendee side-


def find_by_code(db: Session, event_id: uuid.UUID, code: str) -> PromoCampaign:
    campaign = db.scalar(select(PromoCampaign).join(PromoCode).where(
        PromoCode.event_id == event_id, PromoCode.code == code.strip().upper()))
    if campaign is None:
        raise AppError("This promo code does not exist for the event", "promo_not_found")
    return campaign


def check_usable(campaign: PromoCampaign) -> None:
    now = utcnow()
    if not campaign.is_active:
        raise AppError("This promo code has been disabled", "promo_disabled")
    if campaign.starts_at and now < campaign.starts_at:
        raise AppError("This promo code is not active yet", "promo_not_started")
    if campaign.ends_at and now >= campaign.ends_at:
        raise AppError("This promo code has expired", "promo_expired")
    if campaign.max_redemptions is not None and campaign.redemption_count >= campaign.max_redemptions:
        raise AppError("This promo code has been fully used", "promo_exhausted")


def applies_to(campaign: PromoCampaign, category_id: uuid.UUID) -> bool:
    allowed = {c.id for c in campaign.ticket_categories}
    return not allowed or category_id in allowed


def unit_discount(campaign: PromoCampaign, unit_price: int) -> int:
    if campaign.discount_type == DiscountType.PERCENT:
        return min(unit_price, round(unit_price * campaign.discount_value / 100))
    return min(unit_price, campaign.discount_value)


def _preview(event: Event, campaign: PromoCampaign) -> PromoPreview:
    return PromoPreview(
        event_id=event.id, event_slug=event.slug, code=campaign.code.code, campaign_name=campaign.name,
        discount_type=campaign.discount_type, discount_value=campaign.discount_value,
        ticket_category_ids=[c.id for c in campaign.ticket_categories],
    )


def preview_code(db: Session, event_id: uuid.UUID, code: str) -> PromoPreview:
    campaign = find_by_code(db, event_id, code)
    check_usable(campaign)
    return _preview(db.get(Event, event_id), campaign)


def resolve_token(db: Session, token: str) -> PromoPreview:
    campaign = db.scalar(select(PromoCampaign).join(PromoCode).where(PromoCode.token == token))
    if campaign is None:
        raise AppError("This campaign link is not valid", "promo_not_found")
    db.execute(update(PromoCampaign).where(PromoCampaign.id == campaign.id)
               .values(visit_count=PromoCampaign.visit_count + 1).execution_options(synchronize_session=False))
    db.commit()
    db.refresh(campaign)
    check_usable(campaign)
    return _preview(db.get(Event, campaign.event_id), campaign)


def reserve_redemption(db: Session, campaign: PromoCampaign, order: Order, user: User, discount: int) -> None:
    now = utcnow()
    result = db.execute(
        update(PromoCampaign)
        .where(
            PromoCampaign.id == campaign.id,
            PromoCampaign.is_active.is_(True),
            or_(PromoCampaign.ends_at.is_(None), PromoCampaign.ends_at > now),
            or_(PromoCampaign.max_redemptions.is_(None), PromoCampaign.redemption_count < PromoCampaign.max_redemptions),
        )
        .values(redemption_count=PromoCampaign.redemption_count + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise Conflict("This promo code has just been fully used", "promo_exhausted")
    db.add(PromoRedemption(campaign_id=campaign.id, order_id=order.id, user_id=user.id, discount_amount=discount))


def _redemption(db: Session, order: Order) -> PromoRedemption | None:
    return db.scalar(select(PromoRedemption).where(PromoRedemption.order_id == order.id))


def confirm_redemption(db: Session, order: Order) -> None:
    redemption = _redemption(db, order)
    if redemption:
        redemption.status = "confirmed"


def release_redemption(db: Session, order: Order) -> None:
    redemption = _redemption(db, order)
    if redemption and redemption.status == "reserved":
        redemption.status = "released"
        db.execute(update(PromoCampaign).where(PromoCampaign.id == redemption.campaign_id, PromoCampaign.redemption_count > 0)
                   .values(redemption_count=PromoCampaign.redemption_count - 1).execution_options(synchronize_session=False))
