import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.audit.services import record
from app.checkin.schemas import CheckInRecordOut, CheckInStats, ScanOut, StaffEventOut, TicketScanInfo
from app.core.database import utcnow
from app.core.security import parse_ticket_qr
from app.events.models import Event, EventStatus, StaffAssignment
from app.shared.exceptions import Conflict, Forbidden, NotFound
from app.tickets.models import CheckInRecord, Ticket, TicketCategory, TicketStatus
from app.users.models import User, UserRole

ADMISSIBLE = (TicketStatus.VALID, TicketStatus.CHECKED_IN)


def get_access(db: Session, user: User, event_id: uuid.UUID) -> tuple[Event, bool]:
    event = db.scalar(select(Event).options(joinedload(Event.venue)).where(Event.id == event_id))
    if event is None:
        raise NotFound("Event not found", "event_not_found")
    if user.role == UserRole.PLATFORM_ADMIN or event.organizer_id == user.id:
        return event, True
    assignment = db.scalar(select(StaffAssignment).where(
        StaffAssignment.event_id == event_id, StaffAssignment.user_id == user.id))
    if assignment is None:
        raise Forbidden("You are not assigned to this event", "not_event_staff")
    return event, assignment.can_undo


def stats(db: Session, event_id: uuid.UUID) -> CheckInStats:
    rows = dict(db.execute(select(Ticket.status, func.count()).where(Ticket.event_id == event_id).group_by(Ticket.status)).all())
    checked_in = rows.get(TicketStatus.CHECKED_IN, 0)
    registered = checked_in + rows.get(TicketStatus.VALID, 0)
    return CheckInStats(registered=registered, checked_in=checked_in, remaining=registered - checked_in)


def staff_events(db: Session, user: User) -> list[StaffEventOut]:
    assigned = {a.event_id: a.can_undo for a in db.scalars(select(StaffAssignment).where(StaffAssignment.user_id == user.id))}
    query = (select(Event).options(joinedload(Event.venue))
             .where(or_(Event.organizer_id == user.id, Event.id.in_(assigned.keys())),
                    Event.status.in_([EventStatus.PUBLISHED, EventStatus.UNPUBLISHED]))
             .order_by(Event.start_at))
    events = [e for e in db.scalars(query) if e.event_class.value != "completed"] or []
    return [StaffEventOut(
        id=e.id, title=e.title, start_at=e.start_at, end_at=e.end_at, timezone=e.timezone, status=e.status.value,
        event_class=e.event_class.value, venue_name=e.venue.name, venue_city=e.venue.city,
        can_undo=assigned.get(e.id, True), stats=stats(db, e.id),
    ) for e in events]


def _info(ticket: Ticket) -> TicketScanInfo:
    seat = f"{ticket.seat_section} · row {ticket.seat_row} · seat {ticket.seat_number}" if ticket.seat_row else None
    return TicketScanInfo(
        id=ticket.id, code=ticket.code, status=ticket.status.value, attendee_name=ticket.attendee_name,
        attendee_email=ticket.attendee_email, ticket_type=ticket.category.name, seat=seat,
        order_number=ticket.order.number, checked_in_at=ticket.checked_in_at,
    )


def _load_ticket(db: Session, ticket_id: uuid.UUID) -> Ticket | None:
    return db.scalar(select(Ticket).options(joinedload(Ticket.category), joinedload(Ticket.order)).where(Ticket.id == ticket_id))


def _record_entry(db: Session, user: User, event_id: uuid.UUID, ticket: Ticket, method: str) -> bool:
    now = utcnow()
    result = db.execute(update(Ticket).where(Ticket.id == ticket.id, Ticket.status == TicketStatus.VALID)
                        .values(status=TicketStatus.CHECKED_IN, checked_in_at=now)
                        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        db.refresh(ticket)
        return False
    db.execute(update(TicketCategory).where(TicketCategory.id == ticket.ticket_category_id)
               .values(checked_in=TicketCategory.checked_in + 1).execution_options(synchronize_session=False))
    db.add(CheckInRecord(ticket_id=ticket.id, event_id=event_id, staff_user_id=user.id, action="check_in", method=method))
    record(db, actor=user, action="checkin.check_in", entity_type="ticket", entity_id=ticket.id, event_id=event_id,
           description=f"{ticket.attendee_name} checked in (ticket {ticket.code}, {method})")
    db.commit()
    db.refresh(ticket)
    return True


def scan(db: Session, user: User, event_id: uuid.UUID, payload: str, check_in: bool = True) -> ScanOut:
    get_access(db, user, event_id)

    def answer(result: str, message: str, ticket: Ticket | None = None) -> ScanOut:
        return ScanOut(result=result, message=message, ticket=_info(ticket) if ticket else None, stats=stats(db, event_id))

    text = payload.strip()
    if text.lower().startswith(("http://", "https://")) or "?c=" in text:
        return answer("campaign_qr", "This is a promotional QR code, not a ticket. Ask for the ticket QR code.")
    ticket_id = parse_ticket_qr(text)
    if ticket_id is None:
        return answer("invalid", "This is not a genuine BiletFlow ticket.")
    ticket = _load_ticket(db, ticket_id)
    if ticket is None:
        return answer("invalid", "This ticket does not exist.")
    if ticket.event_id != event_id:
        return answer("wrong_event", "This ticket is for a different event.", ticket)
    if ticket.status == TicketStatus.CANCELLED:
        return answer("cancelled", "This ticket was cancelled.", ticket)
    if ticket.status == TicketStatus.REFUNDED:
        return answer("refunded", "This ticket was refunded.", ticket)
    if ticket.status == TicketStatus.CHECKED_IN:
        return answer("already_used", "This ticket has already been used.", ticket)
    if check_in and not _record_entry(db, user, event_id, ticket, "scan"):
        return answer("already_used", "This ticket has already been used.", ticket)
    return answer("valid", "Welcome! Entry recorded." if check_in else "The ticket is valid.", ticket)


def _event_ticket(db: Session, event_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket:
    ticket = _load_ticket(db, ticket_id)
    if ticket is None or ticket.event_id != event_id:
        raise NotFound("Ticket not found for this event", "ticket_not_found")
    return ticket


def manual_check_in(db: Session, user: User, event_id: uuid.UUID, ticket_id: uuid.UUID) -> ScanOut:
    get_access(db, user, event_id)
    ticket = _event_ticket(db, event_id, ticket_id)
    if ticket.status != TicketStatus.VALID:
        raise Conflict(f"This ticket cannot be checked in (status: {ticket.status.value})", f"ticket_{ticket.status.value}")
    if not _record_entry(db, user, event_id, ticket, "manual"):
        raise Conflict("This ticket has already been used", "ticket_checked_in")
    return ScanOut(result="valid", message="Entry recorded.", ticket=_info(ticket), stats=stats(db, event_id))


def undo(db: Session, user: User, event_id: uuid.UUID, ticket_id: uuid.UUID) -> ScanOut:
    _, can_undo = get_access(db, user, event_id)
    if not can_undo:
        raise Forbidden("You are not allowed to undo check-ins for this event", "undo_not_allowed")
    ticket = _event_ticket(db, event_id, ticket_id)
    result = db.execute(update(Ticket).where(Ticket.id == ticket.id, Ticket.status == TicketStatus.CHECKED_IN)
                        .values(status=TicketStatus.VALID, checked_in_at=None).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        raise Conflict("This ticket is not checked in", "ticket_not_checked_in")
    db.execute(update(TicketCategory).where(TicketCategory.id == ticket.ticket_category_id, TicketCategory.checked_in > 0)
               .values(checked_in=TicketCategory.checked_in - 1).execution_options(synchronize_session=False))
    db.add(CheckInRecord(ticket_id=ticket.id, event_id=event_id, staff_user_id=user.id, action="undo", method="manual"))
    record(db, actor=user, action="checkin.undo", entity_type="ticket", entity_id=ticket.id, event_id=event_id,
           description=f"Check-in of {ticket.attendee_name} reversed (ticket {ticket.code})")
    db.commit()
    db.refresh(ticket)
    return ScanOut(result="valid", message="Check-in reversed. The ticket can be used again.", ticket=_info(ticket),
                   stats=stats(db, event_id))


def search(db: Session, user: User, event_id: uuid.UUID, q: str | None, limit: int = 50) -> list[TicketScanInfo]:
    get_access(db, user, event_id)
    from app.orders.models import Order

    query = (select(Ticket).options(joinedload(Ticket.category), joinedload(Ticket.order))
             .join(Order, Ticket.order_id == Order.id).where(Ticket.event_id == event_id)
             .order_by(Ticket.attendee_name, Ticket.code).limit(limit))
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(or_(Ticket.attendee_name.ilike(like), Ticket.attendee_email.ilike(like),
                                Ticket.code.ilike(like), Order.number.ilike(like)))
    return [_info(t) for t in db.scalars(query)]


def recent(db: Session, user: User, event_id: uuid.UUID, limit: int = 30) -> list[CheckInRecordOut]:
    get_access(db, user, event_id)
    query = (select(CheckInRecord).options(joinedload(CheckInRecord.ticket), joinedload(CheckInRecord.staff))
             .where(CheckInRecord.event_id == event_id).order_by(CheckInRecord.created_at.desc()).limit(limit))
    return [CheckInRecordOut(id=r.id, action=r.action, method=r.method, created_at=r.created_at, staff_name=r.staff.name,
                             ticket_code=r.ticket.code, attendee_name=r.ticket.attendee_name) for r in db.scalars(query)]
