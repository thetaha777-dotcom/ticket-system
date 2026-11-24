import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import services as auth_services
from app.auth.dependencies import get_current_user
from app.auth.schemas import Message
from app.core.database import get_db
from app.notifications import services as notifications
from app.users import services
from app.users.models import User
from app.users.schemas import (
    ChangePasswordRequest,
    NotificationOut,
    OrganizerProfileIn,
    OrganizerProfileOut,
    PayoutAccountIn,
    UserOut,
    UserUpdate,
)


router = APIRouter(prefix="/users/me", tags=["users"])

@router.get("", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.patch("", response_model=UserOut)
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.update_me(db, user, data)


@router.post("/change-password", response_model=Message)
def change_password(data: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_services.change_password(db, user, data.current_password, data.new_password)
    return Message(detail="Password updated")



@router.get("/organizer-profile", response_model=OrganizerProfileOut)
def read_profile(user: User = Depends(get_current_user)):
    return services.get_profile(user)


@router.put("/organizer-profile", response_model=OrganizerProfileOut)
def save_profile(data: OrganizerProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.upsert_profile(db, user, data)


@router.post("/organizer-profile/verify-identity", response_model=OrganizerProfileOut)
def verify_identity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.verify_identity(db, user)


@router.put("/payout-account", response_model=OrganizerProfileOut)
def set_payout_account(data: PayoutAccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.set_payout_account(db, user, data)




@router.get("/notifications", response_model=list[NotificationOut])
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notifications.list_for_user(db, user)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications.mark_read(db, user)


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_one(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications.mark_read(db, user, notification_id)
