from __future__ import annotations

from app.infrastructure.db import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, func


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    target_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "refresh_token",
    "access_token",
    "authorization",
    "api_key",
    "secret",
    "code",
    "source_code",
    "hidden_tests",
}


def _safe_metadata(metadata):
    return {
        str(key): value
        for key, value in (metadata or {}).items()
        if str(key).lower() not in _SENSITIVE_KEYS
    }


def record_audit(
    session,
    event_type,
    actor_user_id=None,
    target_id=None,
    ip_address=None,
    metadata=None,
):
    import json

    event = AuditEvent(
        event_type=event_type,
        actor_user_id=actor_user_id,
        target_id=str(target_id) if target_id is not None else None,
        ip_address=ip_address,
        metadata_json=json.dumps(_safe_metadata(metadata), sort_keys=True),
    )
    session.add(event)
    session.flush()
    return event
