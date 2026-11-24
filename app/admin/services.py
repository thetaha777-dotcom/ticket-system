import csv
import io
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.activation.models import ActivationStatus, PaidSalesActivation
from app.admin.schemas import (
    ActivationRow,
    AdminEventRow,
    AdminOrderRow,
    Overview,
    PromoActivityRow,
    ReportRow,
    UserAdminUpdate,
)
from app.audit.services import record
from app.events.models import Event, EventReport, EventStatus
from app.notifications.services import notify
from app.orders.models import Order, OrderStatus, Payment, PaymentKind, PaymentStatus, Refund
from app.promos.models import PromoCampaign
from app.promos.services import campaign_stats
from app.shared.exceptions import AppError, NotFound
from app.support.models import CaseKind, CaseStatus, SupportCase
from app.tickets.models import Ticket
from app.users.models import User, UserRole
from app.users.schemas import UserBrief


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def overview(db: Session) -> Overview:
    gross = db.scalar(select(func.coalesce(func.sum(Order.subtotal), 0))
                      .where(Order.status.in_([OrderStatus.COMPLETED, OrderStatus.REFUNDED])))
    return Overview(
        users=_count(db, User),
        organizers=_count(db, User, User.role == UserRole.ORGANIZER),
        events_published=_count(db, Event, Event.status == EventStatus.PUBLISHED),
        events_suspended=_count(db, Event, Event.is_suspended.is_(True)),
        orders_completed=_count(db, Order, Order.status == OrderStatus.COMPLETED),
        tickets_issued=_count(db, Ticket),
        gross_sales=gross,
        refunds_total=db.scalar(select(func.coalesce(func.sum(Refund.amount), 0))),
        payment_failures=_count(db, Payment, Payment.status == PaymentStatus.FAILED),
        activations_active=_count(db, PaidSalesActivation, PaidSalesActivation.status == ActivationStatus.ACTIVE),
        activations_suspended=_count(db, PaidSalesActivation, PaidSalesActivation.status == ActivationStatus.SUSPENDED),
        open_reports=_count(db, EventReport, EventReport.status == "open"),
        open_support_cases=_count(db, SupportCase, SupportCase.status != CaseStatus.RESOLVED,
                                  or_(SupportCase.kind == CaseKind.ORGANIZER, SupportCase.is_escalated.is_(True))),
    )



def list_users(db: Session, q: str | None, role: UserRole | None, limit: int, offset: int) -> tuple[list[User], int]:
    conditions = []
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(User.name.ilike(like), User.email.ilike(like)))
    if role:
        conditions.append(User.role == role)
    total = _count(db, User, *conditions)
    users = db.scalars(select(User).where(*conditions).order_by(User.created_at.desc()).limit(limit).offset(offset))
    return list(users), total


def update_user(db: Session, admin: User, user_id: uuid.UUID, data: UserAdminUpdate) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found", "user_not_found")
    if user.id == admin.id:
        raise AppError("You cannot change your own administrator account here", "cannot_change_self")
    if data.is_active is not None and data.is_active != user.is_active:
        user.is_active = data.is_active
        record(db, actor=admin, action="user.reactivated" if data.is_active else "user.suspended", entity_type="user",
               entity_id=user.id, description=f"Account {user.email} {'reactivated' if data.is_active else 'suspended'}")
    if data.role is not None and data.role != user.role:
        record(db, actor=admin, action="user.role_changed", entity_type="user", entity_id=user.id,
               description=f"Role of {user.email}: {user.role.value} → {data.role.value}")
        user.role = data.role
    db.commit()
    return user




def list_events(db: Session, q: str | None, suspended: bool | None, limit: int, offset: int) -> tuple[list[AdminEventRow], int]:
    conditions = []
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(Event.title.ilike(like), Event.slug.ilike(like)))
    if suspended is not None:
        conditions.append(Event.is_suspended.is_(suspended))
    total = _count(db, Event, *conditions)
    query = (select(Event).options(joinedload(Event.organizer), selectinload(Event.ticket_categories))
             .where(*conditions).order_by(Event.created_at.desc()).limit(limit).offset(offset))
    rows = []
    for event in db.scalars(query):
        rows.append(AdminEventRow(
            id=event.id, slug=event.slug, title=event.title, status=event.status.value, visibility=event.visibility.value,
            is_suspended=event.is_suspended, suspended_reason=event.suspended_reason, start_at=event.start_at,
            organizer=UserBrief.model_validate(event.organizer),
            tickets_sold=sum(c.sold for c in event.ticket_categories),
            open_reports=_count(db, EventReport, EventReport.event_id == event.id, EventReport.status == "open"),
        ))
    return rows, total


def set_event_suspended(db: Session, admin: User, event_id: uuid.UUID, reason: str | None) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFound("Event not found", "event_not_found")
    event.is_suspended = reason is not None
    event.suspended_reason = reason
    description = f"Event suspended by a platform administrator: {reason}" if reason else "Event suspension lifted"
    record(db, actor=admin, action="event.suspended" if reason else "event.unsuspended", entity_type="event",
           entity_id=event.id, event_id=event.id, description=description)
    notify(db, db.get(User, event.organizer_id), "event_moderation", f"Moderation update for «{event.title}»", description,
           link=f"/organizer/events/{event.id}")
    db.commit()
    return event




def list_orders(db: Session, q: str | None, status: OrderStatus | None, limit: int, offset: int) -> tuple[list[AdminOrderRow], int]:
    conditions = []
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(Order.number.ilike(like), Order.buyer_email.ilike(like), Order.buyer_name.ilike(like)))
    if status:
        conditions.append(Order.status == status)
    total = _count(db, Order, *conditions)
    query = (select(Order).options(joinedload(Order.event)).where(*conditions)
             .order_by(Order.created_at.desc()).limit(limit).offset(offset))
    rows = [AdminOrderRow(
        id=o.id, number=o.number, status=o.status, total=o.total, quantity=o.quantity, buyer_name=o.buyer_name,
        buyer_email=o.buyer_email, event_id=o.event_id, event_title=o.event.title, promo_code=o.promo_code,
        created_at=o.created_at) for o in db.scalars(query)]
    return rows, total


def list_payments(db: Session, q: str | None, status: PaymentStatus | None, kind: PaymentKind | None,
                  limit: int, offset: int) -> list[Payment]:
    query = select(Payment).order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    if q:
        # payment reference, order number, or the name / email of the person who paid
        like = f"%{q.strip()}%"
        query = (query.join(User, User.id == Payment.user_id).outerjoin(Order, Order.id == Payment.order_id)
                 .where(or_(Payment.provider_reference.ilike(like), Order.number.ilike(like),
                            User.email.ilike(like), User.name.ilike(like))))
    if status:
        query = query.where(Payment.status == status)
    if kind:
        query = query.where(Payment.kind == kind)
    return list(db.scalars(query))


def list_refunds(db: Session, limit: int, offset: int) -> list[Refund]:
    return list(db.scalars(select(Refund).order_by(Refund.created_at.desc()).limit(limit).offset(offset)))




def list_activations(db: Session) -> list[ActivationRow]:
    query = (select(PaidSalesActivation, Event, User).join(Event, PaidSalesActivation.event_id == Event.id)
             .join(User, PaidSalesActivation.organizer_id == User.id).order_by(PaidSalesActivation.created_at.desc()))
    return [ActivationRow(
        id=a.id, event_id=e.id, event_title=e.title, organizer=UserBrief.model_validate(u), status=a.status,
        fee_amount=a.fee_amount, fee_paid=a.fee_paid, terms_accepted=a.terms_accepted, activated_at=a.activated_at,
        suspended_reason=a.suspended_reason, created_at=a.created_at) for a, e, u in db.execute(query).all()]


def _report_row(report: EventReport) -> ReportRow:
    return ReportRow(
        id=report.id, event_id=report.event_id, event_title=report.event.title, event_slug=report.event.slug,
        event_suspended=report.event.is_suspended, reporter=UserBrief.model_validate(report.reporter),
        reason=report.reason, status=report.status, resolution_note=report.resolution_note, created_at=report.created_at,
    )


def list_reports(db: Session, status: str | None) -> list[ReportRow]:
    query = (select(EventReport).options(joinedload(EventReport.event), joinedload(EventReport.reporter))
             .order_by(EventReport.created_at.desc()))
    if status:
        query = query.where(EventReport.status == status)
    return [_report_row(r) for r in db.scalars(query)]


def review_report(db: Session, admin: User, report_id: uuid.UUID, status: str, note: str | None) -> ReportRow:
    report = db.scalar(select(EventReport).options(joinedload(EventReport.event), joinedload(EventReport.reporter))
                       .where(EventReport.id == report_id))
    if report is None:
        raise NotFound("Report not found", "report_not_found")
    report.status, report.resolution_note, report.reviewed_by_id = status, note, admin.id
    record(db, actor=admin, action="report.reviewed", entity_type="event_report", entity_id=report.id,
           event_id=report.event_id, description=f"Event report marked as {status}")
    db.commit()
    return _report_row(report)


def promo_activity(db: Session) -> list[PromoActivityRow]:
    query = (select(PromoCampaign, Event).join(Event, PromoCampaign.event_id == Event.id)
             .order_by(PromoCampaign.created_at.desc()).limit(200))
    rows = []
    for campaign, event in db.execute(query).all():
        stats = campaign_stats(db, campaign)
        rows.append(PromoActivityRow(
            campaign_id=campaign.id, event_id=event.id, event_title=event.title, name=campaign.name,
            code=campaign.code.code, is_active=campaign.is_active, max_redemptions=campaign.max_redemptions,
            redemptions=stats.redemptions, discount_amount=stats.discount_amount, net_revenue=stats.net_revenue,
        ))
    return rows




def export_csv(db: Session, report: str) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    if report == "orders":
        writer.writerow(["number", "status", "event", "buyer_name", "buyer_email", "tickets", "subtotal_kzt",
                         "discount_kzt", "total_kzt", "promo_code", "created_at", "completed_at"])
        for o in db.scalars(select(Order).options(joinedload(Order.event)).order_by(Order.created_at)):
            writer.writerow([o.number, o.status.value, o.event.title, o.buyer_name, o.buyer_email, o.quantity, o.subtotal,
                             o.discount_total, o.total, o.promo_code or "", o.created_at.isoformat(),
                             o.paid_at.isoformat() if o.paid_at else ""])
    elif report == "payments":
        writer.writerow(["reference", "kind", "status", "amount_kzt", "processing_fee_kzt", "simulation", "failure_reason",
                         "created_at"])
        for p in db.scalars(select(Payment).order_by(Payment.created_at)):
            writer.writerow([p.provider_reference, p.kind.value, p.status.value, p.amount, p.processing_fee,
                             "yes" if p.is_simulation else "no", p.failure_reason or "", p.created_at.isoformat()])
    elif report == "users":
        writer.writerow(["name", "email", "role", "verified", "active", "created_at"])
        for u in db.scalars(select(User).order_by(User.created_at)):
            writer.writerow([u.name, u.email, u.role.value, u.is_verified, u.is_active, u.created_at.isoformat()])
    elif report == "events":
        writer.writerow(["title", "status", "suspended", "visibility", "organizer_email", "start_at", "tickets_sold"])
        query = select(Event).options(joinedload(Event.organizer), selectinload(Event.ticket_categories)).order_by(Event.start_at)
        for e in db.scalars(query):
            writer.writerow([e.title, e.status.value, e.is_suspended, e.visibility.value, e.organizer.email,
                             e.start_at.isoformat(), sum(c.sold for c in e.ticket_categories)])
    else:
        raise NotFound("Unknown report", "report_not_found")
    return out.getvalue()
