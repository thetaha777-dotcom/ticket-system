"""Ticket types (inventory) and issued tickets."""
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.audit.services import record
from app.core.database import utcnow
from app.core.security import ticket_qr_payload
from app.events.models import Event, EventStatus, StaffAssignment
from app.orders.models import Order, OrderItem
from app.shared.exceptions import AppError, Conflict, Forbidden, NotFound
from app.shared.utils import format_kzt, random_code
from app.tickets.models import Ticket, TicketCategory, TicketStatus, TicketType
from app.tickets.schemas import EventBrief, TicketOut, TicketTypeIn, TicketTypePublic, TicketTypeUpdate
from app.users.models import User, UserRole



def get_category(db: Session, event: Event, category_id: uuid.UUID) -> TicketCategory:
    category = db.get(TicketCategory, category_id)
    if category is None or category.event_id != event.id:
        raise NotFound("Ticket type not found", "ticket_type_not_found")
    return category


def create_ticket_type(db: Session, event: Event, user: User, data: TicketTypeIn) -> TicketCategory:
    if event.status == EventStatus.CANCELLED:
        raise Conflict("A cancelled event cannot be changed", "event_cancelled")
    category = TicketCategory(event_id=event.id, sort_order=len(event.ticket_categories), **data.model_dump())
    event.ticket_categories.append(category)
    db.flush()
    record(db, actor=user, action="ticket_type.created", entity_type="ticket_type", entity_id=category.id, event_id=event.id,
           description=f"Ticket type «{category.name}» created: {format_kzt(category.price)}, {category.quantity} tickets")
    db.commit()
    return category


def update_ticket_type(db: Session, event: Event, user: User, category: TicketCategory, data: TicketTypeUpdate) -> TicketCategory:
    changes = data.model_dump(exclude_unset=True)
    notes = []
    if "price" in changes and changes["price"] != category.price:
        if category.type == TicketType.FREE and changes["price"] != 0:
            raise AppError("A free ticket type cannot have a price. Create a paid ticket type instead.", "free_ticket_price")
        if category.type == TicketType.PAID and changes["price"] <= 0:
            raise AppError("A paid ticket type needs a price above 0", "paid_ticket_price")
        notes.append(f"price {format_kzt(category.price)} → {format_kzt(changes['price'])}")
    if "quantity" in changes and changes["quantity"] != category.quantity:
        if changes["quantity"] < category.sold + category.reserved:
            raise Conflict(
                f"Quantity cannot go below the {category.sold + category.reserved} tickets already sold or reserved",
                "quantity_below_sold",
            )
        notes.append(f"quantity {category.quantity} → {changes['quantity']}")
    if "hidden" in changes and changes["hidden"] != category.hidden:
        notes.append("hidden" if changes["hidden"] else "visible again")
    for field, value in changes.items():
        setattr(category, field, value)
    if category.sale_start and category.sale_end and category.sale_end <= category.sale_start:
        raise AppError("Sales must end after they start", "invalid_sale_window")
    record(db, actor=user, action="ticket_type.updated", entity_type="ticket_type", entity_id=category.id, event_id=event.id,
           description=f"Ticket type «{category.name}» updated" + (": " + ", ".join(notes) if notes else ""))
    db.commit()
    return category


def delete_ticket_type(db: Session, event: Event, user: User, category: TicketCategory) -> None:
    used = db.scalar(select(func.count()).select_from(OrderItem).where(OrderItem.ticket_category_id == category.id))
    if used:
        raise Conflict("This ticket type already has orders. Hide it instead of deleting it.", "ticket_type_in_use")
    record(db, actor=user, action="ticket_type.deleted", entity_type="ticket_type", entity_id=category.id, event_id=event.id,
           description=f"Ticket type «{category.name}» deleted")
    event.ticket_categories.remove(category)
    db.commit()


def to_public(category: TicketCategory, event: Event, paid_sales_active: bool) -> TicketTypePublic:
    """What an attendee sees, including the reason a type cannot be bought right now."""
    now = utcnow()
    reason = None
    if not event.is_on_sale:
        reason = "event_closed"
    elif category.type == TicketType.PAID and not paid_sales_active:
        reason = "paid_sales_inactive"
    elif category.sale_start and now < category.sale_start:
        reason = "not_started"
    elif category.sale_end and now >= category.sale_end:
        reason = "ended"
    elif category.available <= 0:
        reason = "sold_out"
    return TicketTypePublic(
        id=category.id, type=category.type, name=category.name, description=category.description, price=category.price,
        order_limit=category.order_limit, available=category.available, sale_start=category.sale_start,
        sale_end=category.sale_end, on_sale=reason is None, unavailable_reason=reason,
    )



def issue_tickets(db: Session, order: Order) -> list[Ticket]:
    attendees = json.loads(order.attendees) if order.attendees else []
    tickets, index = [], 0
    for item in order.items:
        for _ in range(item.quantity):
            person = attendees[index] if index < len(attendees) else {}
            ticket = Ticket(
                code=f"{random_code(4)}-{random_code(4)}",
                event_id=order.event_id, ticket_category_id=item.ticket_category_id, order_id=order.id,
                order_item_id=item.id, event_seat_id=item.event_seat_id,
                attendee_name=person.get("name") or order.buyer_name,
                attendee_email=person.get("email") or order.buyer_email,
                seat_section=item.seat_section, seat_row=item.seat_row, seat_number=item.seat_number,
            )
            db.add(ticket)
            tickets.append(ticket)
            index += 1
    db.flush()
    return tickets


def event_brief(event: Event) -> EventBrief:
    return EventBrief(
        id=event.id, slug=event.slug, title=event.title, start_at=event.start_at, end_at=event.end_at,
        timezone=event.timezone, status=event.status.value, image=event.images[0] if event.images else None,
        venue_name=event.venue.name, venue_address=event.venue.address, venue_city=event.venue.city,
    )


def ticket_out(ticket: Ticket) -> TicketOut:
    usable = ticket.status in (TicketStatus.VALID, TicketStatus.CHECKED_IN)
    return TicketOut(
        id=ticket.id, code=ticket.code, status=ticket.status, event_id=ticket.event_id, order_id=ticket.order_id,
        order_number=ticket.order.number, ticket_type=ticket.category.name, attendee_name=ticket.attendee_name,
        attendee_email=ticket.attendee_email, seat_section=ticket.seat_section, seat_row=ticket.seat_row,
        seat_number=ticket.seat_number, issued_at=ticket.issued_at, checked_in_at=ticket.checked_in_at,
        qr_payload=ticket_qr_payload(ticket.id) if usable else None, event=event_brief(ticket.event),
    )


def _ticket_query():
    return select(Ticket).options(
        joinedload(Ticket.event).joinedload(Event.venue), joinedload(Ticket.category), joinedload(Ticket.order)
    )


def list_my_tickets(db: Session, user: User) -> list[Ticket]:
    query = _ticket_query().join(Order, Ticket.order_id == Order.id).where(Order.user_id == user.id).order_by(Ticket.issued_at.desc())
    return list(db.scalars(query))


def get_ticket_for_user(db: Session, ticket_id: uuid.UUID, user: User) -> Ticket:
    ticket = db.scalar(_ticket_query().where(Ticket.id == ticket_id))
    if ticket is None:
        raise NotFound("Ticket not found", "ticket_not_found")
    if ticket.order.user_id == user.id or user.role == UserRole.PLATFORM_ADMIN or ticket.event.organizer_id == user.id:
        return ticket
    is_staff = db.scalar(select(StaffAssignment.id).where(
        StaffAssignment.event_id == ticket.event_id, StaffAssignment.user_id == user.id))
    if not is_staff:
        raise Forbidden("This ticket belongs to another account", "not_your_ticket")
    return ticket
