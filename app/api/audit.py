"""Audit Log API — admin-only JSON."""

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.audit import get_audit_logs

router = APIRouter(prefix="/api/audit-logs", tags=["api-audit"])


@router.get("")
async def api_audit_logs(request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return {"ok": False, "error": "需要管理员权限"}
    logs = get_audit_logs(db, limit=200)
    return {
        "ok": True,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else "system",
                "action": log.action,
                "target_type": log.entity_type,
                "target_id": log.entity_id,
                "detail": log.details,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
