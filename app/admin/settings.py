from sqlalchemy.orm import Session

from app.admin.models import PlatformSetting
from app.core.config import settings
from app.users.models import User

# key -> (type, default)
SETTINGS = {
    "activation_fee_kzt": (int, settings.activation_fee_kzt),
    "processing_fee_percent": (float, settings.processing_fee_percent),
    "order_hold_minutes": (int, settings.order_hold_minutes),
}


def get_setting(db: Session, key: str):
    cast, default = SETTINGS[key]
    row = db.get(PlatformSetting, key)
    return cast(row.value) if row else default


def all_settings(db: Session) -> dict:
    return {key: get_setting(db, key) for key in SETTINGS}


def update_settings(db: Session, user: User, values: dict) -> dict:
    for key, value in values.items():
        if key not in SETTINGS or value is None:
            continue
        row = db.get(PlatformSetting, key)
        if row is None:
            db.add(PlatformSetting(key=key, value=str(value), updated_by_id=user.id))
        else:
            row.value, row.updated_by_id = str(value), user.id
    db.flush()
    return all_settings(db)
