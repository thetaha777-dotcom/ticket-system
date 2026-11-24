import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_organizer
from app.core.database import get_db
from app.events import services
from app.events.models import Event
from app.users.models import User


def managed_event(event_id: uuid.UUID, user: User = Depends(require_organizer), db: Session = Depends(get_db)) -> Event:
    return services.get_managed_event(db, event_id, user)
