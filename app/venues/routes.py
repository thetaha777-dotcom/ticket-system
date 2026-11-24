import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_organizer
from app.core.database import get_db
from app.users.models import User
from app.venues import services
from app.venues.schemas import VenueIn, VenueLayoutOut, VenueOut

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=list[VenueOut])
def list_venues(q: str | None = None, db: Session = Depends(get_db)):
    return services.list_venues(db, q)


@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(data: VenueIn, user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    return services.create_venue(db, user, data)


@router.get("/{venue_id}", response_model=VenueOut)
def get_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)):
    return services.get_venue(db, venue_id)


@router.get("/{venue_id}/layout", response_model=VenueLayoutOut)
def get_layout(venue_id: uuid.UUID, db: Session = Depends(get_db)):
    return services.get_layout(db, venue_id)
