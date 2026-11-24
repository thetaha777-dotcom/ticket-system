import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.activation.services import is_paid_sales_active
from app.audit.services import record
from app.core.database import utcnow
from app.events.models import (
    Event,
    EventReport,
    EventSeat,
    EventStatus,
    EventVisibility,
    Seating,
    SeatStatus,
    StaffAssignment,
)
from app.events.schemas import EventDetail, EventIn, EventManage, EventStats, EventUpdate
from app.notifications.services import notify
from app.orders.models import Order, OrderStatus
from app.shared.exceptions import AppError, Conflict, Forbidden, NotFound
from app.shared.ics import build_event_ics
from app.shared.utils import format_local, slugify
from app.tickets import services as ticket_services
from app.tickets.models import Ticket, TicketCategory, TicketStatus
from app.tickets.schemas import TicketTypeOut
from app.users.models import User, UserRole
from app.venues.models import Venue


def _event_query():
    return select(Event).options(
        selectinload(Event.ticket_categories), joinedload(Event.venue),
        joinedload(Event.organizer).joinedload(User.organizer_profile),
    )


def get_event(db: Session, event_id: uuid.UUID) -> Event:
    event = db.scalar(_event_query().where(Event.id == event_id))
    if event is None:
        raise NotFound("Event not found", "event_not_found")
    return event


def get_event_by_ref(db: Session, ref: str) -> Event:
    try:
        condition = Event.id == uuid.UUID(ref)
    except ValueError:
        condition = Event.slug == ref
    event = db.scalar(_event_query().where(condition))
    if event is None:
        raise NotFound("Event not found", "event_not_found")
    return event


def can_manage(user: User | None, event: Event) -> bool:
    return user is not None and (user.role == UserRole.PLATFORM_ADMIN or event.organizer_id == user.id)


def get_managed_event(db: Session, event_id: uuid.UUID, user: User) -> Event:
    event = get_event(db, event_id)
    if not can_manage(user, event):
        raise Forbidden("You do not manage this event", "not_event_manager")
    return event


def staff_assignment(db: Session, user: User, event_id: uuid.UUID) -> StaffAssignment | None:
    return db.scalar(select(StaffAssignment).where(StaffAssignment.event_id == event_id, StaffAssignment.user_id == user.id))



def list_public(db: Session, *, q: str | None = None, category: str | None = None, city: str | None = None,
                date_from: datetime | None = None, date_to: datetime | None = None,
                limit: int = 24, offset: int = 0) -> tuple[list[Event], int]:
    conditions = [
        Event.status == EventStatus.PUBLISHED, Event.visibility == EventVisibility.PUBLIC,
        Event.is_suspended.is_(False), Event.end_at >= (date_from or utcnow()),
    ]
    if date_to:
        conditions.append(Event.start_at <= date_to)
    if category:
        conditions.append(Event.category == category)
    if city:
        conditions.append(Event.venue.has(Venue.city.ilike(city)))
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(Event.title.ilike(like), Event.description.ilike(like), Event.venue.has(Venue.name.ilike(like))))
    total = db.scalar(select(func.count()).select_from(Event).where(*conditions))
    events = db.scalars(_event_query().where(*conditions).order_by(Event.start_at).limit(limit).offset(offset))
    return list(events), total


def list_filters(db: Session) -> dict:
    base = [Event.status == EventStatus.PUBLISHED, Event.visibility == EventVisibility.PUBLIC,
            Event.is_suspended.is_(False), Event.end_at >= utcnow()]
    categories = db.scalars(select(Event.category).where(*base).distinct().order_by(Event.category))
    cities = db.scalars(select(Venue.city).join(Event, Event.venue_id == Venue.id).where(*base).distinct().order_by(Venue.city))
    return {"categories": list(categories), "cities": list(cities)}


def get_visible_event(db: Session, ref: str, user: User | None, access_key: str | None = None) -> Event:
    event = get_event_by_ref(db, ref)
    if can_manage(user, event) or (user is not None and staff_assignment(db, user, event.id) is not None):
        return event
    if event.status in (EventStatus.DRAFT, EventStatus.UNPUBLISHED):
        raise NotFound("Event not found", "event_not_found")
    if event.visibility == EventVisibility.PRIVATE and access_key != event.access_key:
        has_order = user is not None and db.scalar(
            select(Order.id).where(Order.event_id == event.id, Order.user_id == user.id).limit(1))
        if not has_order:
            raise Forbidden("This is a private event. Open it with the invitation link from the organizer.", "event_private")
    return event


def public_detail(db: Session, event: Event, user: User | None) -> EventDetail:
    paid_active = is_paid_sales_active(db, event.id)
    detail = EventDetail.model_validate(event)
    detail.paid_sales_active = paid_active
    detail.can_manage = can_manage(user, event)
    detail.ticket_types = [ticket_services.to_public(c, event, paid_active) for c in event.ticket_categories if not c.hidden]
    return detail



def event_stats(db: Session, event: Event) -> EventStats:
    sold = sum(c.sold for c in event.ticket_categories)
    total_quantity = sum(c.quantity for c in event.ticket_categories)
    orders, gross = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(Order.event_id == event.id, Order.status == OrderStatus.COMPLETED)).one()
    return EventStats(
        capacity=min(total_quantity, event.capacity) if event.capacity else total_quantity,
        tickets_sold=sold, tickets_reserved=sum(c.reserved for c in event.ticket_categories),
        checked_in=sum(c.checked_in for c in event.ticket_categories), orders=orders, gross_sales=gross,
    )


def manage_detail(db: Session, event: Event) -> EventManage:
    detail = EventManage.model_validate(event)
    detail.paid_sales_active = is_paid_sales_active(db, event.id)
    detail.ticket_types = [TicketTypeOut.model_validate(c) for c in event.ticket_categories]
    detail.stats = event_stats(db, event)
    return detail


def list_for_organizer(db: Session, user: User, group: str | None = None) -> list[EventManage]:
    query = _event_query().where(Event.organizer_id == user.id).order_by(Event.start_at.desc())
    result = []
    for event in db.scalars(query):
        is_draft = event.status in (EventStatus.DRAFT, EventStatus.UNPUBLISHED)
        event_group = "draft" if is_draft else event.event_class.value
        if group is None or group == event_group:
            result.append(manage_detail(db, event))
    return result


def _check_venue_for_seating(db: Session, venue_id: uuid.UUID, seating: Seating) -> None:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFound("Venue not found", "venue_not_found")
    if seating == Seating.ASSIGNED_SEATING and not venue.has_seat_map:
        raise AppError("Assigned seating needs a venue that has a seat map", "venue_without_seat_map")


def create_event(db: Session, user: User, data: EventIn) -> Event:
    _check_venue_for_seating(db, data.venue_id, data.seating)
    event = Event(organizer_id=user.id, slug=slugify(data.title), access_key=secrets.token_urlsafe(9), **data.model_dump())
    db.add(event)
    db.flush()
    record(db, actor=user, action="event.created", entity_type="event", entity_id=event.id, event_id=event.id,
           description=f"Event «{event.title}» created as a draft")
    db.commit()
    return get_event(db, event.id)


def _has_sales(db: Session, event: Event) -> bool:
    return any(c.sold or c.reserved for c in event.ticket_categories)


def _ticket_holders(db: Session, event: Event) -> list[User]:
    query = (select(User).join(Order, Order.user_id == User.id)
             .where(Order.event_id == event.id, Order.status == OrderStatus.COMPLETED).distinct())
    return list(db.scalars(query))


def update_event(db: Session, event: Event, user: User, data: EventUpdate) -> Event:
    if event.status == EventStatus.CANCELLED:
        raise Conflict("A cancelled event cannot be changed", "event_cancelled")
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if getattr(event, k) != v}
    if not changes:
        return event
    start, end = changes.get("start_at", event.start_at), changes.get("end_at", event.end_at)
    if end <= start:
        raise AppError("The event must end after it starts", "invalid_dates")
    if ("seating" in changes or "venue_id" in changes):
        if _has_sales(db, event):
            raise Conflict("Venue and seating cannot change after tickets have been sold", "has_sales")
        _check_venue_for_seating(db, changes.get("venue_id", event.venue_id), changes.get("seating", event.seating))
        db.execute(delete(EventSeat).where(EventSeat.event_id == event.id))   # the old seat map no longer applies
    if "capacity" in changes and changes["capacity"] is not None:
        used = sum(c.sold + c.reserved for c in event.ticket_categories)
        if changes["capacity"] < used:
            raise Conflict(f"Capacity cannot go below the {used} tickets already sold or reserved", "capacity_below_sold")

    notes = []
    if "capacity" in changes:
        notes.append(f"capacity {event.capacity or '∞'} → {changes['capacity'] or '∞'}")
    schedule_changed = any(k in changes for k in ("start_at", "end_at", "venue_id", "timezone"))
    if schedule_changed:
        notes.append("date, time or venue")
    other = [k for k in changes if k not in ("capacity", "start_at", "end_at", "venue_id", "timezone")]
    notes.extend(other)

    for field, value in changes.items():
        setattr(event, field, value)
    if schedule_changed:
        event.sequence += 1
    db.flush()
    record(db, actor=user, action="event.updated", entity_type="event", entity_id=event.id, event_id=event.id,
           description="Event updated: " + ", ".join(notes))
    db.commit()
    event = get_event(db, event.id)

    if schedule_changed and event.status == EventStatus.PUBLISHED:
        ics = ("event.ics", "text/calendar", build_event_ics(event, event.venue).encode("utf-8"))
        for holder in _ticket_holders(db, event):
            notify(db, holder, "event_update", f"«{event.title}» has been updated",
                   f"The organizer changed the date, time or venue.\nNew time: {format_local(event.start_at, event.timezone)}\n"
                   f"Venue: {event.venue.name}, {event.venue.address}, {event.venue.city}\n"
                   "Your tickets stay valid. The attached calendar file updates your calendar entry.",
                   link=f"/e/{event.slug}", attachments=[ics])
        db.commit()
    return event


def publish(db: Session, event: Event, user: User) -> Event:
    if event.status not in (EventStatus.DRAFT, EventStatus.UNPUBLISHED):
        raise Conflict("Only a draft or unpublished event can be published", "invalid_status")
    if event.is_suspended:
        raise Conflict("This event is suspended by the platform", "event_suspended")
    if not user.is_verified and user.role != UserRole.PLATFORM_ADMIN:
        raise AppError("Confirm your email address before publishing an event", "email_not_verified")
    if event.end_at <= utcnow():
        raise AppError("The event dates are in the past", "event_in_past")
    if not any(not c.hidden for c in event.ticket_categories):
        raise AppError("Add at least one visible ticket type before publishing", "no_ticket_types")
    if event.seating == Seating.ASSIGNED_SEATING:
        configured = db.scalar(select(func.count()).select_from(EventSeat).where(
            EventSeat.event_id == event.id, EventSeat.ticket_category_id.is_not(None)))
        if not configured:
            raise AppError("Configure the seat map before publishing", "seating_not_configured")
    event.status = EventStatus.PUBLISHED
    event.published_at = utcnow()
    record(db, actor=user, action="event.published", entity_type="event", entity_id=event.id, event_id=event.id,
           description="Event published")
    db.commit()
    return event


def unpublish(db: Session, event: Event, user: User) -> Event:
    if event.status != EventStatus.PUBLISHED:
        raise Conflict("Only a published event can be unpublished", "invalid_status")
    event.status = EventStatus.UNPUBLISHED
    record(db, actor=user, action="event.unpublished", entity_type="event", entity_id=event.id, event_id=event.id,
           description="Event unpublished: it is hidden and registration is paused. Issued tickets stay valid.")
    db.commit()
    return event


def cancel(db: Session, event: Event, user: User, reason: str | None) -> Event:
    from app.orders.services import cancel_event_orders

    if event.status == EventStatus.CANCELLED:
        raise Conflict("The event is already cancelled", "event_cancelled")
    event.status = EventStatus.CANCELLED
    event.cancelled_at = utcnow()
    event.sequence += 1
    record(db, actor=user, action="event.cancelled", entity_type="event", entity_id=event.id, event_id=event.id,
           description="Event cancelled" + (f": {reason}" if reason else ""))
    db.commit()
    cancel_event_orders(db, event, user, reason)
    return get_event(db, event.id)


def duplicate(db: Session, event: Event, user: User) -> Event:
    start, end = event.start_at, event.end_at
    if start <= utcnow():
        shift = timedelta(days=((utcnow() - start).days // 7 + 5) * 7)
        start, end = start + shift, end + shift
    copy = Event(
        organizer_id=user.id if user.role != UserRole.PLATFORM_ADMIN else event.organizer_id,
        slug=slugify(event.title), access_key=secrets.token_urlsafe(9),
        title=f"{event.title} (copy)"[:255], description=event.description, category=event.category,
        images=list(event.images), venue_id=event.venue_id, timezone=event.timezone, start_at=start, end_at=end,
        capacity=event.capacity, visibility=event.visibility, seating=event.seating, refund_policy=event.refund_policy,
        refund_policy_text=event.refund_policy_text, duplicated_from_id=event.id,
    )
    db.add(copy)
    db.flush()
    category_map = {}
    for old in event.ticket_categories:
        new = TicketCategory(event_id=copy.id, type=old.type, name=old.name, description=old.description, price=old.price,
                             order_limit=old.order_limit, quantity=old.quantity, hidden=old.hidden, sort_order=old.sort_order)
        db.add(new)
        db.flush()
        category_map[old.id] = new.id
    for seat in db.scalars(select(EventSeat).where(EventSeat.event_id == event.id)):
        blocked = seat.status == SeatStatus.UNAVAILABLE
        db.add(EventSeat(event_id=copy.id, seat_id=seat.seat_id, ticket_category_id=category_map.get(seat.ticket_category_id),
                         status=SeatStatus.UNAVAILABLE if blocked else SeatStatus.AVAILABLE))
    record(db, actor=user, action="event.duplicated", entity_type="event", entity_id=copy.id, event_id=copy.id,
           description=f"Draft created as a copy of «{event.title}»")
    record(db, actor=user, action="event.duplicated", entity_type="event", entity_id=event.id, event_id=event.id,
           description="Event duplicated into a new draft")
    db.commit()
    return get_event(db, copy.id)



def list_staff(db: Session, event: Event) -> list[StaffAssignment]:
    query = (select(StaffAssignment).options(joinedload(StaffAssignment.user))
             .where(StaffAssignment.event_id == event.id).order_by(StaffAssignment.created_at))
    return list(db.scalars(query))


def assign_staff(db: Session, event: Event, actor: User, email: str, can_undo: bool) -> StaffAssignment:
    person = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if person is None:
        raise NotFound("No BiletFlow account uses this email. Ask the person to register first.", "user_not_found")
    if person.id == event.organizer_id:
        raise AppError("The organizer can already check attendees in", "already_organizer")
    if staff_assignment(db, person, event.id):
        raise Conflict("This person is already assigned to the event", "already_assigned")
    assignment = StaffAssignment(event_id=event.id, user_id=person.id, can_undo=can_undo, created_by_id=actor.id)
    db.add(assignment)
    db.flush()
    record(db, actor=actor, action="staff.assigned", entity_type="staff_assignment", entity_id=assignment.id,
           event_id=event.id, description=f"{person.name} ({person.email}) assigned as Event Admin")
    notify(db, person, "staff_assignment", f"You are an Event Admin for «{event.title}»",
           "Sign in to the BiletFlow Check-in mobile app with this account to scan tickets at the entrance.\n"
           f"Event starts: {format_local(event.start_at, event.timezone)}", link=None)
    db.commit()
    return assignment


def remove_staff(db: Session, event: Event, actor: User, assignment_id: uuid.UUID) -> None:
    assignment = db.get(StaffAssignment, assignment_id)
    if assignment is None or assignment.event_id != event.id:
        raise NotFound("Staff assignment not found", "assignment_not_found")
    record(db, actor=actor, action="staff.removed", entity_type="staff_assignment", entity_id=assignment.id,
           event_id=event.id, description=f"{assignment.user.name} removed from the Event Admins")
    db.delete(assignment)
    db.commit()


def report_event(db: Session, event: Event, user: User, reason: str) -> EventReport:
    report = EventReport(event_id=event.id, reporter_id=user.id, reason=reason)
    db.add(report)
    db.commit()
    return report


def checked_in_count(db: Session, event_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(Ticket).where(
        Ticket.event_id == event_id, Ticket.status == TicketStatus.CHECKED_IN))
