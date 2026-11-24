import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.activation.models import ActivationStatus


class ChecklistStep(BaseModel):
    key: str     # paid_ticket_type | identity_verified | payout_account | fee_paid | terms_accepted
    done: bool


class ActivationOut(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    status: ActivationStatus
    is_active: bool
    fee_amount: int
    currency: str = "KZT"
    steps: list[ChecklistStep]
    activated_at: datetime | None
    suspended_reason: str | None
    is_simulation: bool = True   # the fee payment and the checks are demonstrations, no real money moves


class PayFeeIn(BaseModel):
    outcome: Literal["success", "failure"] = Field("success", description="Result the payment simulator should produce")


class SuspendIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
