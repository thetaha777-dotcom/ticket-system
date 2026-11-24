import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_organizer
from app.core.database import get_db
from app.events.dependencies import managed_event
from app.events.models import Event
from app.promos import services
from app.promos.schemas import CampaignIn, CampaignOut, CampaignUpdate, PromoCheckIn, PromoPreview
from app.users.models import User

router = APIRouter(prefix="/promo", tags=["promo codes"])


@router.post("/check", response_model=PromoPreview)
def check_code(data: PromoCheckIn, db: Session = Depends(get_db)):
    """Is this typed promo code usable for the event? The discount itself is always calculated by /orders/quote."""
    return services.preview_code(db, data.event_id, data.code)


@router.get("/resolve", response_model=PromoPreview)
def resolve_token(token: str, db: Session = Depends(get_db)):
    """Called when a Campaign QR link is opened: returns the event and the promo code to pre-apply."""
    return services.resolve_token(db, token)


organizer_router = APIRouter(prefix="/organizer/events/{event_id}/campaigns", tags=["organizer: promo campaigns"])


@organizer_router.get("", response_model=list[CampaignOut])
def list_campaigns(event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    """Campaigns with exact redemption and revenue figures."""
    return services.list_campaigns(db, event)


@organizer_router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignIn, event: Event = Depends(managed_event), user: User = Depends(require_organizer),
                    db: Session = Depends(get_db)):
    """Creates the campaign together with its unique promo code and Campaign QR link."""
    return services.campaign_out(db, event, services.create_campaign(db, event, user, data))


@organizer_router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: uuid.UUID, data: CampaignUpdate, event: Event = Depends(managed_event),
                    user: User = Depends(require_organizer), db: Session = Depends(get_db)):
    """Rename, change the limit / end date, or disable and re-enable the code."""
    campaign = services.get_campaign(db, event, campaign_id)
    return services.campaign_out(db, event, services.update_campaign(db, event, user, campaign, data))


@organizer_router.get("/{campaign_id}/qr.png")
def campaign_qr(campaign_id: uuid.UUID, event: Event = Depends(managed_event), db: Session = Depends(get_db)):
    """Campaign QR image (teal, framed, labelled 'NOT A TICKET')."""
    campaign = services.get_campaign(db, event, campaign_id)
    return Response(content=services.campaign_qr(event, campaign), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="promo-{campaign.code.code}.png"'})
