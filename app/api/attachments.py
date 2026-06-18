"""Attachments API — upload, download, delete (JSON)."""

import os
import uuid
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.attachment import Attachment
from app.models.contract import Contract
from app.services.audit import log_action
from app.config import settings

router = APIRouter(prefix="/api/attachments", tags=["api-attachments"])


def _get_user(request: Request):
    return {
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


@router.post("/contracts/{contract_id}")
async def api_upload_attachment(
    contract_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}

    contract = db.query(Contract).get(contract_id)
    if not contract:
        return {"ok": False, "error": "合同不存在"}

    if file.content_type not in settings.allowed_mime_types:
        return {"ok": False, "error": f"不支持的文件类型: {file.content_type}。仅支持 PDF、DOC、DOCX"}

    content = await file.read()
    if len(content) > settings.max_upload_size:
        return {"ok": False, "error": f"文件大小超过限制 (最大 {settings.max_upload_size // (1024 * 1024)}MB)"}

    os.makedirs(settings.upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "file")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.upload_dir, stored_name)

    with open(stored_path, "wb") as f:
        f.write(content)

    attachment = Attachment(
        contract_id=contract_id,
        filename=file.filename or "unknown",
        stored_path=stored_path,
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by=u["user_id"],
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    log_action(db, u["user_id"], "create", "attachment", attachment.id,
               {"filename": file.filename, "contract_id": contract_id})

    return {
        "ok": True,
        "attachment": {
            "id": attachment.id,
            "filename": attachment.filename,
            "file_size": attachment.file_size,
            "mime_type": attachment.mime_type,
            "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
        },
    }


@router.get("/{attachment_id}/download")
async def api_download_attachment(attachment_id: int, request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}

    attachment = db.query(Attachment).get(attachment_id)
    if not attachment or not os.path.exists(attachment.stored_path):
        return {"ok": False, "error": "附件不存在"}

    return FileResponse(
        path=attachment.stored_path,
        filename=attachment.filename,
        media_type=attachment.mime_type,
    )


@router.delete("/{attachment_id}")
async def api_delete_attachment(attachment_id: int, request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}

    attachment = db.query(Attachment).get(attachment_id)
    if not attachment:
        return {"ok": False, "error": "附件不存在"}

    contract_id = attachment.contract_id

    if os.path.exists(attachment.stored_path):
        os.remove(attachment.stored_path)

    log_action(db, u["user_id"], "delete", "attachment", attachment_id,
               {"filename": attachment.filename, "contract_id": contract_id})

    db.delete(attachment)
    db.commit()

    return {"ok": True}
