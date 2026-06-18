"""Auth API — login, logout, current user (JSON)."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import verify_password
from app.services.user import get_user_by_username
from app.config import settings

from fastapi import Depends

router = APIRouter(prefix="/api/auth", tags=["api-auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def api_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate and return user info as JSON."""
    user = get_user_by_username(db, body.username)

    if not user:
        return {"ok": False, "error": "用户名或密码错误"}
    if user.status == "disabled":
        return {"ok": False, "error": "账户已被禁用，请联系管理员"}
    if not verify_password(body.password, user.password_hash):
        return {"ok": False, "error": "用户名或密码错误"}

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role

    return {
        "ok": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "status": user.status,
        },
    }


@router.get("/me")
async def api_me(request: Request):
    """Return current user info from session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return {"ok": False, "error": "未登录"}
    return {
        "ok": True,
        "user": {
            "id": user_id,
            "username": request.session.get("username"),
            "role": request.session.get("role"),
        },
    }


@router.post("/logout")
async def api_logout(request: Request):
    """Clear session."""
    request.session.clear()
    return {"ok": True}
