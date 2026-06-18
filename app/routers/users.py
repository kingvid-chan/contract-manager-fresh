"""User management routes — admin only."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_db
from app.services.user import (
    get_user_by_id, get_user_by_username, list_users,
    create_user, update_user, delete_user, toggle_user_status, reset_password,
)
from app.services.audit import log_action
from app.schemas.user import UserCreate, UserUpdate, UserResetPassword
from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])

templates = None  # set by main.py


def require_admin(request: Request):
    """Check session for admin role. Return None if ok, error response if not."""
    if request.session.get("role") != "admin":
        return True  # flag for template-level handling
    return None


@router.get("")
async def user_list(request: Request, db: Session = Depends(get_db)):
    """List all users (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    users = list_users(db)
    error_msg = request.query_params.get("error", "")
    success_msg = request.query_params.get("success", "")
    return tmpl.TemplateResponse("users/list.html", {
        "request": request,
        "users": users,
        "error": error_msg,
        "success": success_msg,
    })


@router.get("/new")
async def user_create_form(request: Request):
    """Show create-user form (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)
    return tmpl.TemplateResponse("users/edit.html", {
        "request": request,
        "user": None,
    })


@router.post("")
async def user_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    error = None
    if get_user_by_username(db, username):
        error = "用户名已存在"

    if error:
        return tmpl.TemplateResponse("users/edit.html", {
            "request": request, "user": None, "error": error,
        }, status_code=400)

    user = create_user(db, username=username, password=password, role=role)
    log_action(db, request.session["user_id"], "create", "user", user.id,
               {"username": username, "role": role})
    return RedirectResponse(url=f"{settings.base_path}/users", status_code=HTTP_302_FOUND)


@router.get("/{user_id}/edit")
async def user_edit_form(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Show edit-user form (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    user = get_user_by_id(db, user_id)
    if not user:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    return tmpl.TemplateResponse("users/edit.html", {
        "request": request,
        "user": user,
    })


@router.post("/{user_id}/edit")
async def user_edit(
    request: Request,
    user_id: int,
    username: str = Form(...),
    role: str = Form("user"),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update a user (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    user = get_user_by_id(db, user_id)
    if not user:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    error = None
    existing = get_user_by_username(db, username)
    if existing and existing.id != user_id:
        error = "用户名已存在"

    if error:
        return tmpl.TemplateResponse("users/edit.html", {
            "request": request, "user": user, "error": error,
        }, status_code=400)

    kwargs = {"username": username, "role": role}
    if password.strip():
        kwargs["password"] = password.strip()

    update_user(db, user, **kwargs)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"username": username, "role": role})
    return RedirectResponse(url=f"{settings.base_path}/users", status_code=HTTP_302_FOUND)


@router.post("/{user_id}/toggle-status")
async def user_toggle_status(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Enable or disable a user (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    user = get_user_by_id(db, user_id)
    if not user:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    # Prevent self-disable
    if user_id == request.session["user_id"]:
        return RedirectResponse(
            url=f"{settings.base_path}/users?error=不能禁用自己",
            status_code=HTTP_302_FOUND,
        )

    toggle_user_status(db, user)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"status": user.status})
    return RedirectResponse(url=f"{settings.base_path}/users", status_code=HTTP_302_FOUND)


@router.post("/{user_id}/reset-password")
async def user_reset_password(
    request: Request,
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Reset a user's password (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    user = get_user_by_id(db, user_id)
    if not user:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    reset_password(db, user, new_password)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"action": "password_reset"})
    return RedirectResponse(url=f"{settings.base_path}/users", status_code=HTTP_302_FOUND)


@router.post("/{user_id}/delete")
async def user_delete(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Delete a user (admin only)."""
    tmpl = request.app.state.templates
    if require_admin(request):
        return tmpl.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    user = get_user_by_id(db, user_id)
    if not user:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    # Prevent self-deletion
    if user_id == request.session["user_id"]:
        return RedirectResponse(
            url=f"{settings.base_path}/users?error=不能删除自己",
            status_code=HTTP_302_FOUND,
        )

    log_action(db, request.session["user_id"], "delete", "user", user_id,
               {"username": user.username})
    delete_user(db, user)
    return RedirectResponse(url=f"{settings.base_path}/users", status_code=HTTP_302_FOUND)
