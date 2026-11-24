from schemas import User
from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.users.models import User
from app.events.models import Event

router = APIRouter()


@router.get("/me")
async def get_current_user_info(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "name": current_user.name,
    }

@router.get("/dashboard")
async def organizer_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "organizer":
        raise HTTPException(status_code=403) #not sure of code
    events = db.query(Event).filter(Event.organizer == current_user.id).all()
    for event in events:
        



    # return {
    #     "linked_suppliers": [],
    #     "recent_orders": [],
    #     "pending_links": []
    # }



# @router.get("/users/me", tags=["users"])
# async def read_user_me():
#     return {"username": "fakecurrentuser"}
#
#
# @router.get("/users/{username}", tags=["users"])
# async def read_user(username: str):
#     return {"username": username}