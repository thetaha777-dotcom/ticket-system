import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at_col, uuid_pk


class AuditLog(Base):

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)   
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))               
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)              
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at_col()