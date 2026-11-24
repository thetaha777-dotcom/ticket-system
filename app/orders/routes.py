import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.events.dependencies import managed_event
from app.events.models import Event
from app.orders import services
from app.orders.models import OrderStatus
from app.orders.schemas import (
    AttendeeRow,
    OrderCreate,
    OrderOut,
    OrderPage,
    PayIn,
    QuoteOut,
    ReasonIn,
    SalesSummary,
)
from app.shared.exceptions import Conflict, Forbidden
from app.shared.pdf import render_tickets_pdf
from app.tickets.models import TicketStatus
from app.users.models import User, UserRole

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/quote", response_model=QuoteOut)
def quote(data: OrderCreate, db: Session = Depends(get_db)):
    return services.quote(db, data)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.order_out(services.create_order(db, user, data))


@router.get("", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [services.order_out(o) for o in services.list_my_orders(db, user)]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order, is_manager = services.get_order_for_user(db, order_id, user)
    return services.order_out(order, for_manager=is_manager)


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay(order_id: uuid.UUID, data: PayIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.order_out(services.pay_order(db, user, order_id, data.outcome))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: uuid.UUID, data: ReasonIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order, is_manager = services.get_order_for_user(db, order_id, user)
    if order.status == OrderStatus.PENDING and order.user_id != user.id:
        raise Forbidden("Only the buyer can abandon a checkout that is still in progress", "not_your_order")
    services.cancel_order(db, order, user, data.reason)
    return services.order_out(services.get_order(db, order_id), for_manager=is_manager)


@router.post("/{order_id}/refund", response_model=OrderOut)
def refund(order_id: uuid.UUID, data: ReasonIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order, is_manager = services.get_order_for_user(db, order_id, user)
    if not is_manager:
        raise Forbidden("Only the organizer can refund an order. Use a support request to ask for a refund.", "not_event_manager")
    services.refund_order(db, order, user, data.reason, force=user.role == UserRole.PLATFORM_ADMIN)
    return services.order_out(services.get_order(db, order_id), for_manager=True)


@router.get("/{order_id}/tickets.pdf")
def order_tickets_pdf(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order, _ = services.get_order_for_user(db, order_id, user)
    tickets = [t for t in order.tickets if t.status in (TicketStatus.VALID, TicketStatus.CHECKED_IN)]
    if not tickets:
        raise Conflict("This order has no valid tickets", "no_valid_tickets")
    for ticket in tickets:
        ticket.event, ticket.order = order.event, order
    return Response(
        content=render_tickets_pdf(tickets), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tickets-{order.number}.pdf"'},
    )



organizer_router = APIRouter(prefix="/organizer/events/{event_id}", tags=["organizer: orders"])


@organizer_router.get("/orders", response_model=OrderPage)
def event_orders(
    q: str | None = None, status: OrderStatus | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    event: Event = Depends(managed_event), db: Session = Depends(get_db),
):
    orders, total = services.list_event_orders(db, event, q=q, status=status, limit=limit, offset=offset)
    return OrderPage(items=[services.order_out(o, for_manager=True) for o in orders], total=total)


@organizer_router.get("/attendees", response_model=list[AttendeeRow])
def event_attendees(q: str | None = None, status: TicketStatus | None = None,
                    event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    return services.list_attendees(db, event, q=q, status=status)


@organizer_router.get("/attendees.csv")
def event_attendees_csv(event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["ticket_code", "status", "attendee_name", "attendee_email", "ticket_type", "seat", "order", "checked_in_at"])
    for row in services.list_attendees(db, event, limit=100_000):
        writer.writerow([row.code, row.status, row.attendee_name, row.attendee_email, row.ticket_type, row.seat or "",
                         row.order_number, row.checked_in_at.isoformat() if row.checked_in_at else ""])
    return Response(content=out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="attendees-{event.slug}.csv"'})


@organizer_router.get("/sales", response_model=SalesSummary)
def event_sales(event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    return services.sales_summary(db, event.id)
