import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.support import services
from app.support.models import CaseStatus
from app.support.schemas import CaseCreate, CaseDetail, CaseOut, CaseUpdate, MessageIn
from app.users.models import User

router = APIRouter(prefix="/support/cases", tags=["support"])


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def open_case(data: CaseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.case_out(db, services.create_case(db, user, data), user, detail=True)


@router.get("", response_model=list[CaseOut])
def list_cases(
    scope: str = Query("mine", pattern="^(mine|managed|platform)$",
                       description="mine = opened by me, managed = cases of my events, platform = admin queue"),
    status: CaseStatus | None = None, event_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return [services.case_out(db, c, user) for c in services.list_cases(db, user, scope, status, event_id)]


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.case_out(db, services.get_case(db, case_id, user), user, detail=True)


@router.post("/{case_id}/messages", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def add_message(case_id: uuid.UUID, data: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = services.get_case(db, case_id, user)
    return services.case_out(db, services.add_message(db, case, user, data.body), user, detail=True)


@router.patch("/{case_id}", response_model=CaseDetail)
def update_case(case_id: uuid.UUID, data: CaseUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = services.get_case(db, case_id, user)
    return services.case_out(db, services.update_case(db, case, user, data), user, detail=True)
