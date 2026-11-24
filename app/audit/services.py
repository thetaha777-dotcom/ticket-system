import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.users.models import User


def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id,
    description: str,
    event_id: uuid.UUID | None = None,
    meta: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_id=event_id,
        actor_id=actor.id if actor else None,
        actor_name=actor.name if actor else "System",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        meta=meta,
    )
    db.add(entry)
    return entry


def list_logs(
    db: Session,
    *,
    event_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    action: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id)
    if event_id:
        query = query.where(AuditLog.event_id == event_id)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
    if action:
        # "refund" matches "refund.completed"; "checkin" matches "checkin.check_in" and "checkin.undo"
        query = query.where(AuditLog.action.like(f"{action}%"))
    return list(db.scalars(query.limit(limit).offset(offset)))
