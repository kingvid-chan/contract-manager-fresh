"""Authentication routes — login and logout."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_db
from app.services.auth import verify_password
from app.services.user import get_user_by_username
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login_page(request: Request):
    """Serve the login HTML page."""
    from fastapi.templating import Jinja2Templates
    templates = request.app.state.templates
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate user and create session."""
    user = get_user_by_username(db, username)

    error = None
    if not user:
        error = "用户名或密码错误"
    elif user.status == "disabled":
        error = "账户已被禁用，请联系管理员"
    elif not verify_password(password, user.password_hash):
        error = "用户名或密码错误"

    if error:
        from fastapi.templating import Jinja2Templates
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": error, "username": username},
            status_code=401,
        )

    # Create session
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role

    return RedirectResponse(url=f"{settings.base_path}/", status_code=HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)
