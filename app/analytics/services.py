import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AttendanceBlock,
    CampaignRow,
    CapacityBlock,
    EventAnalytics,
    OrganizerSummary,
    RevenueBlock,
    SalesPoint,
    TicketTypeRow,
)
from app.core.database import utcnow
from app.events.models import Event, EventStatus
from app.orders.models import Order, OrderItem, OrderStatus
from app.promos.models import PromoCampaign
from app.shared.utils import to_zone
from app.tickets.models import Ticket, TicketCategory, TicketStatus
from app.users.models import User


def _percent(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


def event_analytics(db: Session, event: Event, *, date_from: datetime | None = None, date_to: datetime | None = None,
                    ticket_type_id: uuid.UUID | None = None) -> EventAnalytics:
    categories = [c for c in event.ticket_categories if ticket_type_id in (None, c.id)]
    category_ids = [c.id for c in categories]

    query = (select(OrderItem, Order).join(Order, OrderItem.order_id == Order.id)
             .where(Order.event_id == event.id, Order.status.in_([OrderStatus.COMPLETED, OrderStatus.REFUNDED]),
                    OrderItem.ticket_category_id.in_(category_ids)))
    if date_from:
        query = query.where(Order.paid_at >= date_from)
    if date_to:
        query = query.where(Order.paid_at <= date_to)
    rows = db.execute(query).all()

    gross = discounts = refunds = 0
    by_day: dict = defaultdict(lambda: {"orders": set(), "tickets": 0, "revenue": 0})
    type_revenue: dict = defaultdict(int)
    campaign_totals: dict = defaultdict(lambda: {"orders": set(), "tickets": 0, "gross": 0, "discount": 0})
    for item, order in rows:
        line_gross = item.unit_price * item.quantity
        gross += line_gross
        discounts += item.discount
        if order.status == OrderStatus.REFUNDED:
            refunds += line_gross - item.discount
        day = by_day[to_zone(order.paid_at, event.timezone).date()]
        day["orders"].add(order.id)
        day["tickets"] += item.quantity
        day["revenue"] += line_gross - item.discount
        type_revenue[item.ticket_category_id] += line_gross - item.discount
        if order.promo_campaign_id:
            totals = campaign_totals[order.promo_campaign_id]
            totals["orders"].add(order.id)
            if item.discount:
                totals["tickets"] += item.quantity
            totals["gross"] += line_gross
            totals["discount"] += item.discount

    total = sum(c.quantity for c in categories)
    if ticket_type_id is None and event.capacity:
        total = min(total, event.capacity)
    sold = sum(c.sold for c in categories)

    ticket_counts = dict(db.execute(
        select(Ticket.status, func.count()).where(Ticket.event_id == event.id, Ticket.ticket_category_id.in_(category_ids))
        .group_by(Ticket.status)).all())
    checked_in = ticket_counts.get(TicketStatus.CHECKED_IN, 0)
    registered = checked_in + ticket_counts.get(TicketStatus.VALID, 0)

    campaigns = []
    for campaign in db.scalars(select(PromoCampaign).where(PromoCampaign.event_id == event.id).order_by(PromoCampaign.created_at)):
        totals = campaign_totals.get(campaign.id, {"orders": set(), "tickets": 0, "gross": 0, "discount": 0})
        campaigns.append(CampaignRow(
            campaign_id=campaign.id, name=campaign.name, code=campaign.code.code, is_active=campaign.is_active,
            redemptions=len(totals["orders"]), tickets=totals["tickets"], gross=totals["gross"],
            discount=totals["discount"], net=totals["gross"] - totals["discount"],
        ))

    return EventAnalytics(
        event_id=event.id, generated_at=utcnow(),
        capacity=CapacityBlock(total=total, sold=sold, remaining=max(total - sold, 0), percent_sold=_percent(sold, total)),
        revenue=RevenueBlock(gross=gross, discounts=discounts, refunds=refunds, net=gross - discounts - refunds),
        sales_over_time=[SalesPoint(date=d, orders=len(v["orders"]), tickets=v["tickets"], revenue=v["revenue"])
                         for d, v in sorted(by_day.items())],
        by_ticket_type=[TicketTypeRow(
            ticket_type_id=c.id, name=c.name, price=c.price, quantity=c.quantity, sold=c.sold, remaining=c.available,
            revenue=type_revenue.get(c.id, 0), checked_in=c.checked_in) for c in categories],
        campaigns=campaigns,
        attendance=AttendanceBlock(registered=registered, checked_in=checked_in, absent=registered - checked_in,
                                   percent=_percent(checked_in, registered)),
    )


def organizer_summary(db: Session, user: User) -> OrganizerSummary:
    events = list(db.scalars(select(Event).where(Event.organizer_id == user.id)))
    event_ids = [e.id for e in events]
    sold, checked_in = db.execute(
        select(func.coalesce(func.sum(TicketCategory.sold), 0), func.coalesce(func.sum(TicketCategory.checked_in), 0))
        .where(TicketCategory.event_id.in_(event_ids))).one()
    net = db.scalar(select(func.coalesce(func.sum(Order.total), 0))
                    .where(Order.event_id.in_(event_ids), Order.status == OrderStatus.COMPLETED))
    now = utcnow()
    upcoming = sum(1 for e in events if e.status == EventStatus.PUBLISHED and e.end_at >= now)
    return OrganizerSummary(events=len(events), upcoming_events=upcoming, tickets_sold=sold, net_revenue=net,
                            checked_in=checked_in)
