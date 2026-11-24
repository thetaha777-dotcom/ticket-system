from sqlalchemy.orm import Session

from app.activation.services import refresh_for_organizer
from app.audit.services import record
from app.core.database import utcnow
from app.notifications.services import notify
from app.shared.exceptions import AppError, NotFound
from app.users.models import OrganizerProfile, PayoutAccount, User, UserRole, VerificationStatus
from app.users.schemas import OrganizerProfileIn, PayoutAccountIn, UserUpdate


def update_me(db: Session, user: User, data: UserUpdate) -> User:
    if data.name is not None:
        user.name = data.name.strip()
    if data.locale is not None:
        user.locale = data.locale
    db.commit()
    return user


def get_profile(user: User) -> OrganizerProfile:
    if user.organizer_profile is None:
        raise NotFound("You do not have an organizer profile yet", "no_organizer_profile")
    return user.organizer_profile


def upsert_profile(db: Session, user: User, data: OrganizerProfileIn) -> OrganizerProfile:
    profile = user.organizer_profile
    if profile is None:
        profile = OrganizerProfile(user_id=user.id, **data.model_dump())
        db.add(profile)
        user.organizer_profile = profile
        if user.role in (UserRole.ATTENDEE, UserRole.EVENT_ADMIN):
            user.role = UserRole.ORGANIZER
    else:
        for field, value in data.model_dump().items():
            setattr(profile, field, value)
    db.commit()
    return profile


def verify_identity(db: Session, user: User) -> OrganizerProfile:
    profile = get_profile(user)
    profile.verification_status = VerificationStatus.VERIFIED
    profile.verified_at = utcnow()
    record(db, actor=user, action="organizer.identity_verified", entity_type="organizer_profile",
           entity_id=profile.id, description="Identity verification completed (simulation)")
    db.flush()
    refresh_for_organizer(db, user)
    db.commit()
    return profile


def set_payout_account(db: Session, user: User, data: PayoutAccountIn) -> OrganizerProfile:
    profile = get_profile(user)
    number = data.account_number.replace(" ", "")
    if len(number) < 4:
        raise AppError("Enter a longer account number", "invalid_account")
    account = profile.payout_account
    if account is None:
        account = PayoutAccount(organizer_profile_id=profile.id, bank_name="", account_holder="", account_last4="")
        db.add(account)
        profile.payout_account = account
    account.bank_name = data.bank_name
    account.account_holder = data.account_holder
    account.account_last4 = number[-4:]
    account.status = "verified"
    record(db, actor=user, action="organizer.payout_connected", entity_type="payout_account",
           entity_id=profile.id, description=f"Payout account ending {account.account_last4} connected (simulation)")
    notify(db, user, "payout_status", "Payout account connected",
           f"Your demonstration payout account ending in {account.account_last4} is verified. "
           "No real money is paid out in this academic version.", link="/organizer/profile")
    db.flush()
    refresh_for_organizer(db, user)
    db.commit()
    return profile
