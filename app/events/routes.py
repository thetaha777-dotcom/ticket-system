import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user, require_organizer
from app.auth.schemas import Message
from app.core.config import settings
from app.core.database import get_db
from app.events import seating, services
from app.events.dependencies import managed_event
from app.events.models import Event
from app.events.schemas import (
    CalendarLinks,
    CancelEventIn,
    EventDetail,
    EventIn,
    EventManage,
    EventPage,
    EventReportIn,
    EventUpdate,
    SeatingConfigIn,
    SeatMapOut,
    StaffIn,
    StaffOut,
)
from app.shared.ics import build_event_ics, calendar_links
from app.users.models import User


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventPage)
def list_events(
    q: str | None = None, category: str | None = None, city: str | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
    limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db),
):
    items, total = services.list_public(db, q=q, category=category, city=city, date_from=date_from, date_to=date_to,
                                        limit=limit, offset=offset)
    return EventPage(items=items, total=total)


@router.get("/filters")
def filters(db: Session = Depends(get_db)) -> dict:
    return services.list_filters(db)


@router.get("/{ref}", response_model=EventDetail)
def get_event(ref: str, access_key: str | None = None, user: User | None = Depends(get_optional_user),
              db: Session = Depends(get_db)):
    event = services.get_visible_event(db, ref, user, access_key)
    return services.public_detail(db, event, user)


@router.get("/{ref}/seats", response_model=SeatMapOut)
def get_seat_map(ref: str, access_key: str | None = None, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    event = services.get_visible_event(db, ref, user, access_key)
    return seating.seat_map(db, event, user)


@router.get("/{ref}/calendar.ics")
def calendar_file(ref: str, access_key: str | None = None, user: User | None = Depends(get_optional_user),
                  db: Session = Depends(get_db)):
    event = services.get_visible_event(db, ref, user, access_key)
    return Response(
        content=build_event_ics(event, event.venue), media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{event.slug}.ics"'},
    )


@router.get("/{ref}/calendar-links", response_model=CalendarLinks)
def calendar_link_list(ref: str, access_key: str | None = None, user: User | None = Depends(get_optional_user),
                       db: Session = Depends(get_db)):
    event = services.get_visible_event(db, ref, user, access_key)
    ics = f"{settings.api_public_url}/api/v1/events/{event.id}/calendar.ics"
    if access_key:
        ics += f"?access_key={access_key}"
    return CalendarLinks(ics=ics, **calendar_links(event, event.venue))


@router.post("/{ref}/report", response_model=Message, status_code=status.HTTP_201_CREATED)
def report_event(ref: str, data: EventReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = services.get_visible_event(db, ref, user)
    services.report_event(db, event, user, data.reason)
    return Message(detail="Thank you. The platform team will review this event.")



organizer_router = APIRouter(prefix="/organizer/events", tags=["organizer: events"])


@organizer_router.get("", response_model=list[EventManage])
def my_events(
    group: str | None = Query(None, pattern="^(draft|upcoming|active|completed|cancelled)$"),
    user: User = Depends(require_organizer), db: Session = Depends(get_db),
):
    return services.list_for_organizer(db, user, group)


@organizer_router.post("", response_model=EventManage, status_code=status.HTTP_201_CREATED)
def create_event(data: EventIn, user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.manage_detail(db, services.create_event(db, user, data))


@organizer_router.get("/{event_id}", response_model=EventManage)
def get_my_event(event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    return services.manage_detail(db, event)


@organizer_router.patch("/{event_id}", response_model=EventManage)
def update_event(data: EventUpdate, event: Event = Depends(managed_event), user: User = Depends(require_organizer),
                 db: Session = Depends(get_db)):
    return services.manage_detail(db, services.update_event(db, event, user, data))


@organizer_router.post("/{event_id}/publish", response_model=EventManage)
def publish(event: Event = Depends(managed_event), user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.manage_detail(db, services.publish(db, event, user))


@organizer_router.post("/{event_id}/unpublish", response_model=EventManage)
def unpublish(event: Event = Depends(managed_event), user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.manage_detail(db, services.unpublish(db, event, user))


@organizer_router.post("/{event_id}/cancel", response_model=EventManage)
def cancel(data: CancelEventIn, event: Event = Depends(managed_event), user: User = Depends(require_organizer),
           db: Session = Depends(get_db)):
    return services.manage_detail(db, services.cancel(db, event, user, data.reason))


@organizer_router.post("/{event_id}/duplicate", response_model=EventManage, status_code=status.HTTP_201_CREATED)
def duplicate(event: Event = Depends(managed_event), user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.manage_detail(db, services.duplicate(db, event, user))



@organizer_router.get("/{event_id}/seating", response_model=SeatMapOut)
def get_seating(event: Event = Depends(managed_event), user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return seating.seat_map(db, event, user)


@organizer_router.put("/{event_id}/seating", response_model=SeatMapOut)
def configure_seating(data: SeatingConfigIn, event: Event = Depends(managed_event),
                      user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return seating.configure(db, event, user, data)



@organizer_router.get("/{event_id}/staff", response_model=list[StaffOut])
def list_staff(event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    return services.list_staff(db, event)


@organizer_router.post("/{event_id}/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def assign_staff(data: StaffIn, event: Event = Depends(managed_event), user: User = Depends(require_organizer),
                 db: Session = Depends(get_db)):
    return services.assign_staff(db, event, user, data.email, data.can_undo)


@organizer_router.delete("/{event_id}/staff/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_staff(assignment_id: uuid.UUID, event: Event = Depends(managed_event),
                 user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    services.remove_staff(db, event, user, assignment_id)
