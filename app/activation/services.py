import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activation.models import ActivationStatus, PaidSalesActivation
from app.activation.schemas import ActivationOut, ChecklistStep
from app.admin.settings import get_setting
from app.audit.services import record
from app.core.database import utcnow
from app.events.models import Event
from app.notifications.services import notify
from app.orders.models import Payment, PaymentKind, PaymentStatus
from app.shared.exceptions import AppError, Conflict, NotFound
from app.shared.utils import format_kzt, random_code
from app.tickets.models import TicketType
from app.users.models import User, VerificationStatus


def get_activation(db: Session, event_id: uuid.UUID) -> PaidSalesActivation | None:
    return db.scalar(select(PaidSalesActivation).where(PaidSalesActivation.event_id == event_id))


def is_paid_sales_active(db: Session, event_id: uuid.UUID) -> bool:
    activation = get_activation(db, event_id)
    return activation is not None and activation.status == ActivationStatus.ACTIVE


def ensure_activation(db: Session, event: Event) -> PaidSalesActivation:
    activation = get_activation(db, event.id)
    if activation is None:
        activation = PaidSalesActivation(
            event_id=event.id, organizer_id=event.organizer_id, fee_amount=get_setting(db, "activation_fee_kzt")
        )
        db.add(activation)
        db.flush()
    return activation


def _steps(db: Session, activation: PaidSalesActivation, event: Event) -> list[ChecklistStep]:
    organizer = db.get(User, event.organizer_id)
    profile = organizer.organizer_profile
    return [
        ChecklistStep(key="paid_ticket_type", done=any(c.type == TicketType.PAID for c in event.ticket_categories)),
        ChecklistStep(key="identity_verified", done=bool(profile and profile.verification_status == VerificationStatus.VERIFIED)),
        ChecklistStep(key="payout_account", done=bool(profile and profile.payout_account and profile.payout_account.status == "verified")),
        ChecklistStep(key="fee_paid", done=activation.fee_paid),
        ChecklistStep(key="terms_accepted", done=activation.terms_accepted),
    ]


def _activate_if_complete(db: Session, activation: PaidSalesActivation, event: Event, actor: User | None) -> None:
    if activation.status != ActivationStatus.PENDING:
        return
    if all(step.done for step in _steps(db, activation, event)):
        activation.status = ActivationStatus.ACTIVE
        activation.activated_at = utcnow()
        record(db, actor=actor, action="activation.activated", entity_type="activation", entity_id=activation.id,
               description="Paid ticket sales activated for this event", event_id=event.id)
        notify(db, db.get(User, event.organizer_id), "payout_status", f"Paid sales are active for «{event.title}»",
               "All activation steps are complete. Attendees can now buy paid tickets (simulated payments).",
               link=f"/organizer/events/{event.id}/activation")


def checklist(db: Session, event: Event, actor: User | None = None) -> ActivationOut:
    activation = ensure_activation(db, event)
    _activate_if_complete(db, activation, event, actor)
    db.commit()
    return ActivationOut(
        id=activation.id, event_id=event.id, status=activation.status,
        is_active=activation.status == ActivationStatus.ACTIVE, fee_amount=activation.fee_amount,
        steps=_steps(db, activation, event), activated_at=activation.activated_at,
        suspended_reason=activation.suspended_reason,
    )


def pay_fee(db: Session, event: Event, user: User, outcome: str = "success") -> ActivationOut:
    activation = ensure_activation(db, event)
    if activation.fee_paid:
        raise Conflict("The activation fee is already paid for this event", "fee_already_paid")
    succeeded = outcome == "success"
    payment = Payment(
        kind=PaymentKind.ACTIVATION_FEE, activation_id=activation.id, event_id=event.id, user_id=user.id,
        amount=activation.fee_amount, status=PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED,
        provider_reference=f"SIM-{random_code(10)}", failure_reason=None if succeeded else "Simulated decline",
    )
    db.add(payment)
    db.flush()
    record(db, actor=user, action="payment.succeeded" if succeeded else "payment.failed", entity_type="payment",
           entity_id=payment.id, event_id=event.id,
           description=f"Activation fee {format_kzt(activation.fee_amount)} - simulated payment {'succeeded' if succeeded else 'failed'}")
    if succeeded:
        activation.fee_paid = True
        activation.fee_paid_at = utcnow()
    else:
        notify(db, user, "payment_failed", "Activation fee payment failed",
               f"The simulated payment of the activation fee for «{event.title}» was declined. You can try again.",
               link=f"/organizer/events/{event.id}/activation")
    db.commit()
    if not succeeded:
        raise AppError("The simulated payment was declined", "payment_failed")
    return checklist(db, event, user)


def accept_terms(db: Session, event: Event, user: User) -> ActivationOut:
    activation = ensure_activation(db, event)
    if not activation.terms_accepted:
        activation.terms_accepted = True
        activation.terms_accepted_at = utcnow()
        record(db, actor=user, action="activation.terms_accepted", entity_type="activation", entity_id=activation.id,
               description="Paid-event terms accepted", event_id=event.id)
    return checklist(db, event, user)


def refresh_for_organizer(db: Session, organizer: User) -> None:
    pending = db.scalars(select(PaidSalesActivation).where(
        PaidSalesActivation.organizer_id == organizer.id, PaidSalesActivation.status == ActivationStatus.PENDING))
    for activation in pending:
        _activate_if_complete(db, activation, db.get(Event, activation.event_id), organizer)


def set_suspended(db: Session, activation_id: uuid.UUID, admin: User, reason: str | None) -> PaidSalesActivation:
    activation = db.get(PaidSalesActivation, activation_id)
    if activation is None:
        raise NotFound("Activation record not found", "activation_not_found")
    event = db.get(Event, activation.event_id)
    if reason:
        activation.status = ActivationStatus.SUSPENDED
        activation.suspended_at, activation.suspended_reason = utcnow(), reason
        description = f"Paid sales suspended by a platform administrator: {reason}"
    else:
        if activation.status != ActivationStatus.SUSPENDED:
            raise Conflict("Paid sales are not suspended", "not_suspended")
        activation.status = ActivationStatus.PENDING
        activation.suspended_at = activation.suspended_reason = None
        _activate_if_complete(db, activation, event, admin)
        description = "Paid sales reinstated by a platform administrator"
    record(db, actor=admin, action="activation.suspended" if reason else "activation.reinstated",
           entity_type="activation", entity_id=activation.id, description=description, event_id=event.id)
    notify(db, db.get(User, event.organizer_id), "payout_status", f"Paid sales update for «{event.title}»", description,
           link=f"/organizer/events/{event.id}/activation")
    db.commit()
    return activation
