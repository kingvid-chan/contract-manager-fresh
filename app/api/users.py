"""Users API — admin-only JSON CRUD."""

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.user import (
    get_user_by_id, get_user_by_username, list_users,
    create_user, update_user, delete_user, toggle_user_status, reset_password,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/users", tags=["api-users"])


def _require_admin(request: Request) -> str | None:
    if request.session.get("role") != "admin":
        return "需要管理员权限"
    return None


def _user_to_dict(u) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    username: str
    role: str = "user"
    password: str = ""


class ResetPassword(BaseModel):
    new_password: str


@router.get("")
async def api_list_users(request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    users = list_users(db)
    return {"ok": True, "users": [_user_to_dict(u) for u in users]}


@router.post("")
async def api_create_user(body: UserCreate, request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    if get_user_by_username(db, body.username):
        return {"ok": False, "error": "用户名已存在"}
    u = create_user(db, username=body.username, password=body.password, role=body.role)
    log_action(db, request.session["user_id"], "create", "user", u.id,
               {"username": body.username, "role": body.role})
    return {"ok": True, "user": _user_to_dict(u)}


@router.put("/{user_id}")
async def api_update_user(user_id: int, body: UserUpdate, request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    u = get_user_by_id(db, user_id)
    if not u:
        return {"ok": False, "error": "用户不存在"}
    existing = get_user_by_username(db, body.username)
    if existing and existing.id != user_id:
        return {"ok": False, "error": "用户名已存在"}
    kwargs = {"username": body.username, "role": body.role}
    if body.password.strip():
        kwargs["password"] = body.password.strip()
    update_user(db, u, **kwargs)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"username": body.username, "role": body.role})
    return {"ok": True, "user": _user_to_dict(u)}


@router.post("/{user_id}/toggle-status")
async def api_toggle_status(user_id: int, request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    u = get_user_by_id(db, user_id)
    if not u:
        return {"ok": False, "error": "用户不存在"}
    if user_id == request.session["user_id"]:
        return {"ok": False, "error": "不能禁用自己"}
    toggle_user_status(db, u)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"status": u.status})
    return {"ok": True, "user": _user_to_dict(u)}


@router.post("/{user_id}/reset-password")
async def api_reset_password(user_id: int, body: ResetPassword, request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    u = get_user_by_id(db, user_id)
    if not u:
        return {"ok": False, "error": "用户不存在"}
    reset_password(db, u, body.new_password)
    log_action(db, request.session["user_id"], "update", "user", user_id,
               {"action": "password_reset"})
    return {"ok": True}


@router.delete("/{user_id}")
async def api_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    err = _require_admin(request)
    if err:
        return {"ok": False, "error": err}
    u = get_user_by_id(db, user_id)
    if not u:
        return {"ok": False, "error": "用户不存在"}
    if user_id == request.session["user_id"]:
        return {"ok": False, "error": "不能删除自己"}
    log_action(db, request.session["user_id"], "delete", "user", user_id,
               {"username": u.username})
    delete_user(db, u)
    return {"ok": True}
