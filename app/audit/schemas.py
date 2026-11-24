import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_name: str
    action: str
    entity_type: str
    entity_id: str
    description: str
    created_at: datetime
