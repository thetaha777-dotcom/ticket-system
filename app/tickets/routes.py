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


organizer_router = APIRouter(prefix="/organizer/events/{event_id}/ticket-types", tags=["organizer: ticket types"])


@organizer_router.get("", response_model=list[TicketTypeOut])
def list_ticket_types(event: Event = Depends(managed_event)):
    return event.ticket_categories


@organizer_router.post("", response_model=TicketTypeOut, status_code=status.HTTP_201_CREATED)
def create_ticket_type(data: TicketTypeIn, event: Event = Depends(managed_event),
                       user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.create_ticket_type(db, event, user, data)


@organizer_router.patch("/{ticket_type_id}", response_model=TicketTypeOut)
def update_ticket_type(ticket_type_id: uuid.UUID, data: TicketTypeUpdate, event: Event = Depends(managed_event),
                       user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    category = services.get_category(db, event, ticket_type_id)
    return services.update_ticket_type(db, event, user, category, data)


@organizer_router.delete("/{ticket_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket_type(ticket_type_id: uuid.UUID, event: Event = Depends(managed_event),
                       user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    services.delete_ticket_type(db, event, user, services.get_category(db, event, ticket_type_id))
