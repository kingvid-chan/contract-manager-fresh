"""Attachment routes — upload, download, and delete."""

import os
import uuid
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_db
from app.models.attachment import Attachment
from app.models.contract import Contract
from app.services.audit import log_action
from app.config import settings

router = APIRouter(prefix="/attachments", tags=["attachments"])


def get_session_user(request: Request) -> dict:
    """Extract user info from session."""
    return {
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


# Attach sub-routes for contract-scoped operations
contract_router = APIRouter(prefix="/contracts/{contract_id}/attachments", tags=["attachments"])


@contract_router.post("")
async def upload_attachment(
    request: Request,
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an attachment to a contract."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = db.query(Contract).get(contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    error = None

    # Validate MIME type
    if file.content_type not in settings.allowed_mime_types:
        error = f"不支持的文件类型: {file.content_type}。仅支持 PDF、DOC、DOCX"

    # Read file content to check size
    content = await file.read()
    if len(content) > settings.max_upload_size:
        error = f"文件大小超过限制 (最大 {settings.max_upload_size // (1024 * 1024)}MB)"

    if error:
        return tmpl.TemplateResponse("contracts/detail.html", {
            "request": request, "contract": contract, "user": user,
            "attachment_error": error, "valid_statuses": [],
        }, status_code=400)

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Generate unique stored filename
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
        uploaded_by=user["user_id"],
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    log_action(db, user["user_id"], "create", "attachment", attachment.id,
               {"filename": file.filename, "contract_id": contract_id})

    return RedirectResponse(
        url=f"{settings.base_path}/contracts/{contract_id}",
        status_code=HTTP_302_FOUND,
    )


@router.get("/{attachment_id}/download")
async def download_attachment(
    request: Request,
    attachment_id: int,
    db: Session = Depends(get_db),
):
    """Download an attachment file."""
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    attachment = db.query(Attachment).get(attachment_id)
    if not attachment:
        return request.app.state.templates.TemplateResponse(
            "errors/404.html", {"request": request}, status_code=404
        )

    if not os.path.exists(attachment.stored_path):
        return request.app.state.templates.TemplateResponse(
            "errors/404.html", {"request": request}, status_code=404
        )

    return FileResponse(
        path=attachment.stored_path,
        filename=attachment.filename,
        media_type=attachment.mime_type,
    )


@router.post("/{attachment_id}/delete")
async def delete_attachment(
    request: Request,
    attachment_id: int,
    db: Session = Depends(get_db),
):
    """Delete an attachment."""
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    attachment = db.query(Attachment).get(attachment_id)
    if not attachment:
        return request.app.state.templates.TemplateResponse(
            "errors/404.html", {"request": request}, status_code=404
        )

    contract_id = attachment.contract_id

    # Remove file from disk
    if os.path.exists(attachment.stored_path):
        os.remove(attachment.stored_path)

    log_action(db, user["user_id"], "delete", "attachment", attachment_id,
               {"filename": attachment.filename, "contract_id": contract_id})

    db.delete(attachment)
    db.commit()

    return RedirectResponse(
        url=f"{settings.base_path}/contracts/{contract_id}",
        status_code=HTTP_302_FOUND,
    )
