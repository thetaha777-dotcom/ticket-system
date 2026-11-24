import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.activation.services import is_paid_sales_active
from app.admin.settings import get_setting
from app.audit.services import record
from app.core.database import utcnow
from app.events.models import Event, EventSeat, EventStatus, RefundPolicy, Seating, SeatStatus
from app.notifications.services import notify
from app.orders.models import Order, OrderItem, OrderStatus, Payment, PaymentKind, PaymentStatus, Refund
from app.orders.schemas import (
    AppliedPromo,
    AttendeeRow,
    OrderCreate,
    OrderItemOut,
    OrderOut,
    PaymentOut,
    QuoteLine,
    QuoteOut,
    RefundOut,
    SalesSummary,
)
from app.promos import services as promos
from app.promos.models import PromoCampaign
from app.shared.exceptions import AppError, Conflict, Forbidden, NotFound
from app.shared.ics import build_event_ics
from app.shared.pdf import render_tickets_pdf
from app.shared.utils import format_kzt, format_local, random_code
from app.tickets import services as ticket_services
from app.tickets.models import Ticket, TicketCategory, TicketStatus, TicketType
from app.users.models import User, UserRole
from app.venues.models import Seat, SeatRow, VenueSection


@dataclass
class Line:
    category: TicketCategory
    quantity: int
    event_seat: EventSeat | None = None
    seat_section: str | None = None
    seat_row: str | None = None
    seat_number: int | None = None
    discount: int = 0

    @property
    def total(self) -> int:
        return self.category.price * self.quantity - self.discount



def _check_event_on_sale(event: Event) -> None:
    now = utcnow()
    if event.status == EventStatus.CANCELLED:
        raise Conflict("This event has been cancelled", "event_cancelled")
    if event.status != EventStatus.PUBLISHED or event.is_suspended:
        raise Conflict("This event is not available for registration", "event_unavailable")
    if event.registration_open_at and now < event.registration_open_at:
        raise Conflict("Registration has not opened yet", "registration_not_open")
    if now >= (event.registration_close_at or event.end_at):
        raise Conflict("Registration is closed", "registration_closed")


def _check_category(category: TicketCategory, quantity: int, paid_active: bool) -> None:
    now = utcnow()
    if category.hidden:
        raise NotFound("Ticket type not found", "ticket_type_not_found")
    if category.type == TicketType.PAID and not paid_active:
        raise Conflict("Paid ticket sales are not active for this event yet", "paid_sales_inactive")
    if category.sale_start and now < category.sale_start:
        raise Conflict(f"Sales of «{category.name}» have not started yet", "sales_not_started")
    if category.sale_end and now >= category.sale_end:
        raise Conflict(f"Sales of «{category.name}» have ended", "sales_ended")
    if quantity > category.order_limit:
        raise AppError(f"At most {category.order_limit} «{category.name}» tickets per order", "order_limit_exceeded")


def _build_lines(db: Session, event: Event, data: OrderCreate) -> list[Line]:
    paid_active = is_paid_sales_active(db, event.id)
    categories = {c.id: c for c in event.ticket_categories}
    lines: list[Line] = []

    if event.seating == Seating.ASSIGNED_SEATING:
        if not data.seat_ids:
            raise AppError("Choose at least one seat", "no_seats_selected")
        if len(set(data.seat_ids)) != len(data.seat_ids):
            raise AppError("A seat was selected twice", "duplicate_seat")
        rows = db.execute(
            select(EventSeat, Seat, SeatRow, VenueSection)
            .join(Seat, EventSeat.seat_id == Seat.id).join(SeatRow, Seat.row_id == SeatRow.id)
            .join(VenueSection, Seat.section_id == VenueSection.id)
            .where(EventSeat.event_id == event.id, EventSeat.id.in_(data.seat_ids))
        ).all()
        if len(rows) != len(data.seat_ids):
            raise NotFound("A selected seat does not exist for this event", "seat_not_found")
        for event_seat, seat, row, section in rows:
            category = categories.get(event_seat.ticket_category_id)
            if category is None:
                raise Conflict("A selected seat is not on sale", "seat_unavailable")
            lines.append(Line(category, 1, event_seat, section.name, row.label, seat.number))
        for category_id, quantity in Counter(line.category.id for line in lines).items():
            _check_category(categories[category_id], quantity, paid_active)
        lines.sort(key=lambda line: (line.seat_section, line.seat_row, line.seat_number))
    else:
        wanted = Counter()
        for item in data.items:
            wanted[item.ticket_category_id] += item.quantity
        if not wanted:
            raise AppError("Choose at least one ticket", "empty_order")
        for category_id, quantity in wanted.items():
            category = categories.get(category_id)
            if category is None:
                raise NotFound("Ticket type not found", "ticket_type_not_found")
            _check_category(category, quantity, paid_active)
            lines.append(Line(category, quantity))
    return lines


def _apply_promo(db: Session, event: Event, lines: list[Line], code: str | None) -> PromoCampaign | None:
    if not code or not code.strip():
        return None
    campaign = promos.find_by_code(db, event.id, code)
    promos.check_usable(campaign)
    applied = False
    for line in lines:
        if promos.applies_to(campaign, line.category.id) and line.category.price > 0:
            line.discount = promos.unit_discount(campaign, line.category.price) * line.quantity
            applied = True
    if not applied:
        raise AppError("This promo code does not apply to the selected tickets", "promo_not_applicable")
    return campaign


def _quote(lines: list[Line], campaign: PromoCampaign | None) -> QuoteOut:
    subtotal = sum(line.category.price * line.quantity for line in lines)
    discount = sum(line.discount for line in lines)
    promo = None
    if campaign:
        promo = AppliedPromo(code=campaign.code.code, campaign_name=campaign.name,
                             discount_type=campaign.discount_type, discount_value=campaign.discount_value)
    return QuoteOut(
        lines=[QuoteLine(
            ticket_category_id=line.category.id, event_seat_id=line.event_seat.id if line.event_seat else None, name=line.category.name,
            quantity=line.quantity, unit_price=line.category.price, discount=line.discount, line_total=line.total,
            seat_section=line.seat_section, seat_row=line.seat_row, seat_number=line.seat_number) for line in lines],
        quantity=sum(line.quantity for line in lines), subtotal=subtotal, discount_total=discount,
        total=subtotal - discount, promo=promo,
    )


def _load_event(db: Session, event_id: uuid.UUID, lock: bool = False) -> Event:
    query = select(Event).where(Event.id == event_id)
    if lock:
        query = query.with_for_update()
    event = db.scalar(query)
    if event is None:
        raise NotFound("Event not found", "event_not_found")
    return event


def quote(db: Session, data: OrderCreate) -> QuoteOut:
    event = _load_event(db, data.event_id)
    _check_event_on_sale(event)
    lines = _build_lines(db, event, data)
    for line in lines:
        if line.event_seat is None and line.category.available < line.quantity:
            raise Conflict(f"Only {line.category.available} «{line.category.name}» tickets are left", "sold_out")
    return _quote(lines, _apply_promo(db, event, lines, data.promo_code))



def _item_counts(order: Order) -> Counter:
    counts = Counter()
    for item in order.items:
        counts[item.ticket_category_id] += item.quantity
    return counts


def create_order(db: Session, user: User, data: OrderCreate) -> Order:
    expire_stale_orders(db, data.event_id)
    try:
        event = _load_event(db, data.event_id, lock=True)
        _check_event_on_sale(event)
        lines = _build_lines(db, event, data)
        campaign = _apply_promo(db, event, lines, data.promo_code)
        priced = _quote(lines, campaign)
        if data.attendees and len(data.attendees) != priced.quantity:
            raise AppError("Give one attendee per ticket, or leave the list empty", "attendee_count_mismatch")

        if event.capacity is not None:
            used = db.scalar(select(func.coalesce(func.sum(TicketCategory.sold + TicketCategory.reserved), 0))
                             .where(TicketCategory.event_id == event.id))
            if used + priced.quantity > event.capacity:
                raise Conflict("The event has reached its capacity", "event_full")

        now = utcnow()
        order = Order(
            number=f"BF-{random_code(8)}", user_id=user.id, event_id=event.id, status=OrderStatus.PENDING,
            subtotal=priced.subtotal, discount_total=priced.discount_total, total=priced.total, quantity=priced.quantity,
            buyer_name=(data.buyer_name or user.name).strip(), buyer_email=(data.buyer_email or user.email).lower(),
            buyer_phone=data.buyer_phone, promo_campaign_id=campaign.id if campaign else None,
            promo_code=campaign.code.code if campaign else None,
            attendees=json.dumps([a.model_dump() for a in data.attendees]) if data.attendees else None,
            expires_at=now + timedelta(minutes=get_setting(db, "order_hold_minutes")),
        )
        db.add(order)
        db.flush()

        per_category = Counter()
        for line in lines:
            per_category[line.category.id] += line.quantity
        for category_id, quantity in per_category.items():
            result = db.execute(
                update(TicketCategory)
                .where(TicketCategory.id == category_id,
                       TicketCategory.quantity - TicketCategory.sold - TicketCategory.reserved >= quantity)
                .values(reserved=TicketCategory.reserved + quantity)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise Conflict("Not enough tickets are left", "sold_out")

        seat_ids = [line.event_seat.id for line in lines if line.event_seat]
        if seat_ids:
            result = db.execute(
                update(EventSeat)
                .where(EventSeat.id.in_(seat_ids), EventSeat.event_id == event.id,
                       or_(EventSeat.status == SeatStatus.AVAILABLE,
                           and_(EventSeat.status == SeatStatus.HELD, EventSeat.held_until < now)))
                .values(status=SeatStatus.HELD, held_until=order.expires_at, order_id=order.id)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != len(seat_ids):
                raise Conflict("One of the selected seats has just been taken. Please choose another seat.", "seat_unavailable")

        if campaign:
            promos.reserve_redemption(db, campaign, order, user, priced.discount_total)

        for line in lines:
            order.items.append(OrderItem(
                ticket_category_id=line.category.id, event_seat_id=line.event_seat.id if line.event_seat else None,
                name=line.category.name, quantity=line.quantity, unit_price=line.category.price, discount=line.discount,
                seat_section=line.seat_section, seat_row=line.seat_row, seat_number=line.seat_number,
            ))
        db.flush()

        if order.total == 0:
            _complete_order(db, order, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_order(db, order.id)



def _complete_order(db: Session, order: Order, buyer: User) -> None:
    for category_id, quantity in _item_counts(order).items():
        db.execute(update(TicketCategory).where(TicketCategory.id == category_id)
                   .values(reserved=TicketCategory.reserved - quantity, sold=TicketCategory.sold + quantity)
                   .execution_options(synchronize_session=False))
    seat_count = sum(1 for item in order.items if item.event_seat_id)
    if seat_count:
        result = db.execute(update(EventSeat)
                            .where(EventSeat.order_id == order.id, EventSeat.status == SeatStatus.HELD)
                            .values(status=SeatStatus.SOLD, held_until=None)
                            .execution_options(synchronize_session=False))
        if result.rowcount != seat_count:
            raise Conflict("The seat reservation has expired. Please start again.", "reservation_expired")
    promos.confirm_redemption(db, order)
    order.status = OrderStatus.COMPLETED
    order.paid_at = utcnow()
    order.expires_at = None
    tickets = ticket_services.issue_tickets(db, order)

    event = order.event
    codes = ", ".join(t.code for t in tickets)
    paid_line = f"Total paid (simulated payment): {format_kzt(order.total)}\n" if order.total else ""
    notify(
        db, buyer, "order_confirmation", f"Your tickets for «{event.title}»",
        f"Order {order.number} is confirmed.\n"
        f"Event: {event.title}\nWhen: {format_local(event.start_at, event.timezone)}\n"
        f"Where: {event.venue.name}, {event.venue.address}, {event.venue.city}\n"
        f"Tickets: {len(tickets)} ({codes})\n{paid_line}"
        "Your QR-code tickets are attached as a printable PDF and are also in your account.",
        link=f"/orders/{order.id}",
        attachments=[
            (f"tickets-{order.number}.pdf", "application/pdf", render_tickets_pdf(tickets)),
            ("event.ics", "text/calendar", build_event_ics(event, event.venue).encode("utf-8")),
        ],
    )


def pay_order(db: Session, user: User, order_id: uuid.UUID, outcome: str) -> Order:
    try:
        order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
        if order is None or order.user_id != user.id:
            raise NotFound("Order not found", "order_not_found")
        if order.status != OrderStatus.PENDING:
            raise Conflict("This order is not waiting for payment", "order_not_pending")
        if order.expires_at and order.expires_at <= utcnow():
            _release_reservation(db, order)
            order.status = OrderStatus.EXPIRED
            db.commit()
            raise Conflict("The reservation has expired. Please start again.", "reservation_expired")
        event = order.event
        if event.status != EventStatus.PUBLISHED or event.is_suspended:
            raise Conflict("This event is not available for registration", "event_unavailable")
        if not is_paid_sales_active(db, event.id):
            raise Conflict("Paid ticket sales are not active for this event", "paid_sales_inactive")

        succeeded = outcome == "success"
        fee = round(order.total * get_setting(db, "processing_fee_percent") / 100) if succeeded else 0
        payment = Payment(
            kind=PaymentKind.TICKET_PURCHASE, order_id=order.id, event_id=event.id, user_id=user.id, amount=order.total,
            processing_fee=fee, status=PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED,
            provider_reference=f"SIM-{random_code(10)}", failure_reason=None if succeeded else "Simulated decline",
        )
        db.add(payment)
        db.flush()
        record(db, actor=user, action="payment.succeeded" if succeeded else "payment.failed", entity_type="payment",
               entity_id=payment.id, event_id=event.id,
               description=f"Order {order.number}: simulated payment of {format_kzt(order.total)} "
                           f"{'succeeded' if succeeded else 'failed'}")
        if succeeded:
            order.processing_fee = fee
            _complete_order(db, order, user)
        else:
            notify(db, user, "payment_failed", f"Payment failed for order {order.number}",
                   f"The simulated payment of {format_kzt(order.total)} for «{event.title}» was declined. "
                   "No tickets were issued. Your reservation is kept until it expires, so you can try again.",
                   link=f"/checkout/{order.id}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_order(db, order_id)



def _release_reservation(db: Session, order: Order) -> None:
    for category_id, quantity in _item_counts(order).items():
        db.execute(update(TicketCategory).where(TicketCategory.id == category_id)
                   .values(reserved=TicketCategory.reserved - quantity).execution_options(synchronize_session=False))
    db.execute(update(EventSeat).where(EventSeat.order_id == order.id, EventSeat.status == SeatStatus.HELD)
               .values(status=SeatStatus.AVAILABLE, held_until=None, order_id=None)
               .execution_options(synchronize_session=False))
    promos.release_redemption(db, order)


def expire_stale_orders(db: Session, event_id: uuid.UUID | None = None) -> int:
    query = select(Order).where(Order.status == OrderStatus.PENDING, Order.expires_at < utcnow())
    if event_id:
        query = query.where(Order.event_id == event_id)
    stale = list(db.scalars(query.with_for_update(skip_locked=True)))
    for order in stale:
        _release_reservation(db, order)
        order.status = OrderStatus.EXPIRED
    db.commit()
    return len(stale)


def _void_tickets(db: Session, order: Order, new_status: TicketStatus) -> int:
    voided = 0
    for ticket in order.tickets:
        if ticket.status not in (TicketStatus.VALID, TicketStatus.CHECKED_IN):
            continue
        values = {"sold": TicketCategory.sold - 1}
        if new_status == TicketStatus.REFUNDED:
            values["refunded"] = TicketCategory.refunded + 1
        if ticket.status == TicketStatus.CHECKED_IN:
            values["checked_in"] = TicketCategory.checked_in - 1
        db.execute(update(TicketCategory).where(TicketCategory.id == ticket.ticket_category_id)
                   .values(**values).execution_options(synchronize_session=False))
        ticket.status = new_status
        voided += 1
    db.execute(update(EventSeat).where(EventSeat.order_id == order.id, EventSeat.status == SeatStatus.SOLD)
               .values(status=SeatStatus.AVAILABLE, order_id=None).execution_options(synchronize_session=False))
    return voided


def refund_eligible(order: Order) -> bool:
    if order.status != OrderStatus.COMPLETED or order.total <= 0:
        return False
    event = order.event
    if event.status == EventStatus.CANCELLED or event.refund_policy == RefundPolicy.ANYTIME:
        return True
    return event.refund_policy == RefundPolicy.BEFORE_EVENT and utcnow() < event.start_at


def cancel_order(db: Session, order: Order, actor: User, reason: str | None = None, *, tell_buyer: bool = True) -> Order:
    if order.status == OrderStatus.PENDING:
        _release_reservation(db, order)
    elif order.status == OrderStatus.COMPLETED:
        if order.total > 0:
            raise Conflict("A paid order is cancelled by refunding it", "use_refund")
        _void_tickets(db, order, TicketStatus.CANCELLED)
        record(db, actor=actor, action="order.cancelled", entity_type="order", entity_id=order.id, event_id=order.event_id,
               description=f"Free registration {order.number} cancelled ({order.quantity} tickets)")
        if tell_buyer:
            notify(db, order.user, "order_cancelled", f"Registration {order.number} was cancelled",
                   f"Your registration for «{order.event.title}» was cancelled and its tickets are no longer valid."
                   + (f"\nReason: {reason}" if reason else ""), link=f"/orders/{order.id}")
    else:
        raise Conflict("This order can no longer be cancelled", "order_not_cancellable")
    order.status = OrderStatus.CANCELLED
    order.cancelled_at, order.cancel_reason, order.expires_at = utcnow(), reason, None
    db.commit()
    return order


def refund_order(db: Session, order: Order, actor: User, reason: str | None = None, *,
                 force: bool = False, tell_buyer: bool = True) -> Order:
    if order.status != OrderStatus.COMPLETED or order.total <= 0:
        raise Conflict("Only a completed paid order can be refunded", "not_refundable")
    if not force and not refund_eligible(order):
        raise Conflict("The event's refund policy does not allow a refund for this order", "refund_not_allowed")
    payment = next((p for p in reversed(order.payments) if p.status == PaymentStatus.SUCCEEDED), None)
    refund = Refund(order_id=order.id, payment_id=payment.id if payment else None, event_id=order.event_id,
                    amount=order.total, reason=reason, initiated_by_id=actor.id)
    db.add(refund)
    _void_tickets(db, order, TicketStatus.REFUNDED)
    order.status = OrderStatus.REFUNDED
    order.processing_fee = 0
    order.cancelled_at, order.cancel_reason = utcnow(), reason
    db.flush()
    record(db, actor=actor, action="refund.completed", entity_type="refund", entity_id=refund.id, event_id=order.event_id,
           description=f"Order {order.number} refunded in full: {format_kzt(refund.amount)} (simulation)")
    if tell_buyer:
        notify(db, order.user, "refund_completed", f"Refund completed for order {order.number}",
               f"{format_kzt(refund.amount)} for «{order.event.title}» was refunded (simulated refund). "
               "The tickets of this order are no longer valid." + (f"\nReason: {reason}" if reason else ""),
               link=f"/orders/{order.id}")
    db.commit()
    return order


def cancel_event_orders(db: Session, event: Event, actor: User, reason: str | None) -> None:
    orders = list(db.scalars(_order_query().where(
        Order.event_id == event.id, Order.status.in_([OrderStatus.PENDING, OrderStatus.COMPLETED]))))
    cancel_ics = ("event-cancelled.ics", "text/calendar", build_event_ics(event, event.venue).encode("utf-8"))
    for order in orders:
        was_completed = order.status == OrderStatus.COMPLETED
        if was_completed and order.total > 0:
            refund_order(db, order, actor, "Event cancelled", force=True, tell_buyer=False)
            outcome = f"Your payment of {format_kzt(order.total)} was refunded (simulated refund)."
        else:
            cancel_order(db, order, actor, "Event cancelled", tell_buyer=False)
            outcome = "Your registration was cancelled."
        if was_completed:
            notify(db, order.user, "event_cancelled", f"«{event.title}» has been cancelled",
                   f"The organizer cancelled this event.{(' Reason: ' + reason) if reason else ''}\n{outcome}\n"
                   "The attached calendar file removes the event from your calendar.",
                   link=f"/orders/{order.id}", attachments=[cancel_ics])
    db.commit()



def _order_query():
    return select(Order).options(
        selectinload(Order.items), selectinload(Order.payments), selectinload(Order.refunds),
        selectinload(Order.tickets).joinedload(Ticket.category),
        joinedload(Order.event).joinedload(Event.venue), joinedload(Order.user),
    )


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(_order_query().where(Order.id == order_id).execution_options(populate_existing=True))
    if order is None:
        raise NotFound("Order not found", "order_not_found")
    return order


def get_order_for_user(db: Session, order_id: uuid.UUID, user: User) -> tuple[Order, bool]:
    order = get_order(db, order_id)
    is_manager = user.role == UserRole.PLATFORM_ADMIN or order.event.organizer_id == user.id
    if order.user_id != user.id and not is_manager:
        raise Forbidden("This order belongs to another account", "not_your_order")
    return order, is_manager


def order_out(order: Order, for_manager: bool = False) -> OrderOut:
    event = order.event
    tickets = []
    for ticket in order.tickets:
        ticket.event, ticket.order = event, order
        tickets.append(ticket_services.ticket_out(ticket))
    return OrderOut(
        id=order.id, number=order.number, status=order.status, event=ticket_services.event_brief(event),
        quantity=order.quantity, subtotal=order.subtotal, discount_total=order.discount_total, total=order.total,
        processing_fee=order.processing_fee if for_manager else None, currency=order.currency,
        buyer_name=order.buyer_name, buyer_email=order.buyer_email, buyer_phone=order.buyer_phone,
        promo_code=order.promo_code, expires_at=order.expires_at, created_at=order.created_at, paid_at=order.paid_at,
        cancelled_at=order.cancelled_at, cancel_reason=order.cancel_reason, refund_eligible=refund_eligible(order),
        items=[OrderItemOut.model_validate(i) for i in order.items], tickets=tickets,
        payments=[PaymentOut.model_validate(p) for p in order.payments],
        refunds=[RefundOut.model_validate(r) for r in order.refunds],
    )


def list_my_orders(db: Session, user: User) -> list[Order]:
    query = _order_query().where(Order.user_id == user.id, Order.status != OrderStatus.EXPIRED).order_by(Order.created_at.desc())
    return list(db.scalars(query))


def list_event_orders(db: Session, event: Event, *, q: str | None = None, status: OrderStatus | None = None,
                      limit: int = 50, offset: int = 0) -> tuple[list[Order], int]:
    conditions = [Order.event_id == event.id]
    if status:
        conditions.append(Order.status == status)
    else:
        conditions.append(Order.status != OrderStatus.EXPIRED)
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(Order.number.ilike(like), Order.buyer_name.ilike(like), Order.buyer_email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(Order).where(*conditions))
    orders = db.scalars(_order_query().where(*conditions).order_by(Order.created_at.desc()).limit(limit).offset(offset))
    return list(orders), total


def list_attendees(db: Session, event: Event, *, q: str | None = None, status: TicketStatus | None = None,
                   limit: int = 500) -> list[AttendeeRow]:
    query = (select(Ticket).options(joinedload(Ticket.category), joinedload(Ticket.order))
             .where(Ticket.event_id == event.id).order_by(Ticket.attendee_name, Ticket.code).limit(limit))
    if status:
        query = query.where(Ticket.status == status)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Ticket.attendee_name.ilike(like), Ticket.attendee_email.ilike(like), Ticket.code.ilike(like)))
    return [attendee_row(t) for t in db.scalars(query)]


def attendee_row(ticket: Ticket) -> AttendeeRow:
    seat = f"{ticket.seat_section} · {ticket.seat_row} · {ticket.seat_number}" if ticket.seat_row else None
    return AttendeeRow(
        ticket_id=ticket.id, code=ticket.code, status=ticket.status.value, attendee_name=ticket.attendee_name,
        attendee_email=ticket.attendee_email, ticket_type=ticket.category.name, seat=seat, order_id=ticket.order_id,
        order_number=ticket.order.number, issued_at=ticket.issued_at, checked_in_at=ticket.checked_in_at,
    )


def sales_summary(db: Session, event_id: uuid.UUID) -> SalesSummary:
    paid = [OrderStatus.COMPLETED, OrderStatus.REFUNDED]
    gross, discounts, count = db.execute(
        select(func.coalesce(func.sum(Order.subtotal), 0), func.coalesce(func.sum(Order.discount_total), 0), func.count(Order.id))
        .where(Order.event_id == event_id, Order.status.in_(paid))).one()
    fees = db.scalar(select(func.coalesce(func.sum(Order.processing_fee), 0))
                     .where(Order.event_id == event_id, Order.status == OrderStatus.COMPLETED))
    refunds, refunded_orders = db.execute(
        select(func.coalesce(func.sum(Refund.amount), 0), func.count(Refund.id)).where(Refund.event_id == event_id)).one()
    net = gross - discounts - refunds
    return SalesSummary(gross_sales=gross, discounts=discounts, refunds=refunds, processing_fees=fees, net_revenue=net,
                        estimated_payout=net - fees, orders=count, refunded_orders=refunded_orders)
