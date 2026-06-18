"""Audit service — records operations for compliance tracking."""

import json
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Record an auditable action in the audit_logs table."""
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
    )
    db.add(log_entry)
    db.commit()
    return log_entry


def get_audit_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    """Return recent audit log entries, newest first."""
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
