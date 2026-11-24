import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import services
from app.analytics.schemas import EventAnalytics, OrganizerSummary
from app.audit.schemas import AuditLogOut
from app.audit.services import list_logs
from app.auth.dependencies import require_organizer
from app.core.database import get_db
from app.events.dependencies import managed_event
from app.events.models import Event
from app.users.models import User

router = APIRouter(prefix="/organizer", tags=["organizer: analytics and history"])


@router.get("/summary", response_model=OrganizerSummary)
def summary(user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.organizer_summary(db, user)


@router.get("/events/{event_id}/analytics", response_model=EventAnalytics)
def analytics(
    date_from: datetime | None = None, date_to: datetime | None = None, ticket_type_id: uuid.UUID | None = None,
    event: Event = Depends(managed_event), db: Session = Depends(get_db),
):
    return services.event_analytics(db, event, date_from=date_from, date_to=date_to, ticket_type_id=ticket_type_id)


@router.get("/events/{event_id}/history", response_model=list[AuditLogOut])
def history(
    date_from: datetime | None = None, date_to: datetime | None = None,
    action: str | None = Query(None, description="Activity type prefix: event, ticket_type, payment, refund, promo, support, checkin, staff, activation"),
    limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
    event: Event = Depends(managed_event), db: Session = Depends(get_db),
):
    return list_logs(db, event_id=event.id, date_from=date_from, date_to=date_to, action=action, limit=limit, offset=offset)
