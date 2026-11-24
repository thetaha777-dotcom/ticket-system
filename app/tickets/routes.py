import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_organizer
from app.core.database import get_db
from app.core.security import ticket_qr_payload
from app.events.dependencies import managed_event
from app.events.models import Event
from app.shared import qr
from app.shared.exceptions import Conflict
from app.shared.pdf import render_tickets_pdf
from app.tickets import services
from app.tickets.models import Ticket, TicketStatus
from app.tickets.schemas import TicketOut, TicketTypeIn, TicketTypeOut, TicketTypeUpdate
from app.users.models import User


router = APIRouter(prefix="/tickets", tags=["tickets"])


def _usable(ticket: Ticket) -> Ticket:
    if ticket.status in (TicketStatus.CANCELLED, TicketStatus.REFUNDED):
        raise Conflict(f"This ticket was {ticket.status.value} and is no longer valid", f"ticket_{ticket.status.value}")
    return ticket


@router.get("", response_model=list[TicketOut])
def my_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [services.ticket_out(t) for t in services.list_my_tickets(db, user)]


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.ticket_out(services.get_ticket_for_user(db, ticket_id, user))


@router.get("/{ticket_id}/qr.png")
def ticket_qr(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = _usable(services.get_ticket_for_user(db, ticket_id, user))
    return Response(content=qr.ticket_qr_png(ticket_qr_payload(ticket.id)), media_type="image/png")


@router.get("/{ticket_id}/pdf")
def ticket_pdf(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = _usable(services.get_ticket_for_user(db, ticket_id, user))
    return Response(
        content=render_tickets_pdf([ticket]), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ticket-{ticket.code}.pdf"'},
    )