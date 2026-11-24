from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.activation import services
from app.activation.schemas import ActivationOut, PayFeeIn
from app.auth.dependencies import require_organizer
from app.core.database import get_db
from app.events.dependencies import managed_event
from app.events.models import Event
from app.users.models import User

router = APIRouter(prefix="/organizer/events/{event_id}/activation", tags=["organizer: paid sales activation"])


@router.get("", response_model=ActivationOut)
def get_checklist(event: Event = Depends(managed_event), user: User = Depends(require_organizer),
                  db: Session = Depends(get_db)):
    return services.checklist(db, event, user)


@router.post("/pay-fee", response_model=ActivationOut)
def pay_fee(data: PayFeeIn, event: Event = Depends(managed_event), user: User = Depends(require_organizer),
            db: Session = Depends(get_db)):
    return services.pay_fee(db, event, user, data.outcome)


@router.post("/accept-terms", response_model=ActivationOut)
def accept_terms(event: Event = Depends(managed_event), user: User = Depends(require_organizer),
                 db: Session = Depends(get_db)):
    return services.accept_terms(db, event, user)
