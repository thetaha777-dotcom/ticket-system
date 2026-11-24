import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.services import record
from app.core.database import utcnow
from app.events.models import Event, EventSeat, Seating, SeatStatus
from app.events.schemas import SeatingConfigIn, SeatMapOut, SeatMapRow, SeatMapSeat, SeatMapSection
from app.orders.models import Order, OrderStatus
from app.shared.exceptions import AppError, Conflict
from app.users.models import User
from app.venues.models import Seat
from app.venues.services import get_layout


def configure(db: Session, event: Event, user: User, data: SeatingConfigIn) -> SeatMapOut:
    if event.seating != Seating.ASSIGNED_SEATING:
        raise AppError("This event uses general admission", "not_assigned_seating")
    if not event.venue.has_seat_map:
        raise AppError("The venue has no seat map", "venue_without_seat_map")
    busy = db.scalar(select(func.count()).select_from(EventSeat).where(
        EventSeat.event_id == event.id, EventSeat.status.in_([SeatStatus.HELD, SeatStatus.SOLD])))
    if busy:
        raise Conflict("The seat map cannot be changed after seats have been reserved or sold", "has_sales")

    categories = {c.id: c for c in event.ticket_categories}
    section_category = {s.section_id: s.ticket_category_id for s in data.sections}
    for category_id in section_category.values():
        if category_id is not None and category_id not in categories:
            raise AppError("A selected ticket type does not belong to this event", "ticket_type_not_found")
    blocked = set(data.unavailable_seat_ids)

    existing = {es.seat_id: es for es in db.scalars(select(EventSeat).where(EventSeat.event_id == event.id))}
    counts: dict[uuid.UUID, int] = {}
    for seat in db.scalars(select(Seat).where(Seat.venue_id == event.venue_id)):
        category_id = section_category.get(seat.section_id)
        status = SeatStatus.UNAVAILABLE if (category_id is None or seat.id in blocked) else SeatStatus.AVAILABLE
        event_seat = existing.get(seat.id)
        if event_seat is None:
            db.add(EventSeat(event_id=event.id, seat_id=seat.id, ticket_category_id=category_id, status=status))
        else:
            event_seat.ticket_category_id, event_seat.status = category_id, status
        if status == SeatStatus.AVAILABLE:
            counts[category_id] = counts.get(category_id, 0) + 1
    for category_id, quantity in counts.items():
        categories[category_id].quantity = quantity
    record(db, actor=user, action="event.seating_configured", entity_type="event", entity_id=event.id, event_id=event.id,
           description=f"Seat map configured: {sum(counts.values())} seats on sale")
    db.commit()
    return seat_map(db, event, user)


def seat_map(db: Session, event: Event, user: User | None) -> SeatMapOut:
    venue = get_layout(db, event.venue_id)
    event_seats = {es.seat_id: es for es in db.scalars(select(EventSeat).where(EventSeat.event_id == event.id))}
    categories = {c.id: c for c in event.ticket_categories}
    my_orders = set()
    if user is not None:
        my_orders = set(db.scalars(select(Order.id).where(
            Order.event_id == event.id, Order.user_id == user.id, Order.status == OrderStatus.PENDING)))
    now = utcnow()

    sections = []
    for section in venue.sections:
        rows, category_id = [], None
        for row in section.rows:
            seats = []
            for seat in row.seats:
                es = event_seats.get(seat.id)
                if es is None:
                    continue
                status = es.status
                if status == SeatStatus.HELD and es.held_until and es.held_until < now:
                    status = SeatStatus.AVAILABLE
                category_id = category_id or es.ticket_category_id
                seats.append(SeatMapSeat(
                    id=es.id, seat_id=seat.id, number=seat.number, is_accessible=seat.is_accessible, status=status,
                    held_by_me=status == SeatStatus.HELD and es.order_id in my_orders,
                ))
            rows.append(SeatMapRow(label=row.label, seats=seats))
        category = categories.get(category_id)
        sections.append(SeatMapSection(
            id=section.id, name=section.name, price_category=section.price_category, ticket_category_id=category_id,
            ticket_type_name=category.name if category else None, price=category.price if category else None, rows=rows,
        ))
    return SeatMapOut(event_id=event.id, configured=bool(event_seats), sections=sections)

