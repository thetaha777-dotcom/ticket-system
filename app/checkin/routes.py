import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.checkin import services
from app.checkin.schemas import CheckInRecordOut, CheckInStats, ScanIn, ScanOut, StaffEventOut, TicketScanInfo
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/checkin", tags=["check-in (mobile app)"])


@router.get("/events", response_model=list[StaffEventOut])
def my_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.staff_events(db, user)


@router.get("/events/{event_id}/stats", response_model=CheckInStats)
def event_stats(event_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    services.get_access(db, user, event_id)
    return services.stats(db, event_id)


@router.post("/events/{event_id}/scan", response_model=ScanOut)
def scan(event_id: uuid.UUID, data: ScanIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.scan(db, user, event_id, data.qr_payload, data.check_in)


@router.get("/events/{event_id}/attendees", response_model=list[TicketScanInfo])
def search_attendees(event_id: uuid.UUID, q: str | None = None, limit: int = Query(50, ge=1, le=200),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.search(db, user, event_id, q, limit)


@router.post("/events/{event_id}/tickets/{ticket_id}/check-in", response_model=ScanOut)
def manual_check_in(event_id: uuid.UUID, ticket_id: uuid.UUID, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return services.manual_check_in(db, user, event_id, ticket_id)


@router.post("/events/{event_id}/tickets/{ticket_id}/undo", response_model=ScanOut)
def undo_check_in(event_id: uuid.UUID, ticket_id: uuid.UUID, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return services.undo(db, user, event_id, ticket_id)


@router.get("/events/{event_id}/recent", response_model=list[CheckInRecordOut])
def recent_activity(event_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.recent(db, user, event_id)
