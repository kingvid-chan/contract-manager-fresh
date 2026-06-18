"""FastAPI application entry point — middleware, routes, static files."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND

from app.config import settings
from app.database import init_db
from app.routers import auth, users, contracts, attachments
from app.api import auth as api_auth
from app.api import contracts as api_contracts
from app.api import users as api_users
from app.api import attachments as api_attachments
from app.api import audit as api_audit


# ── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=None,
    redoc_url=None,
)


# ── Pure ASGI Middleware: Cache-Control ──────────────────────────────────────

class CacheControlMiddleware:
    """Add Cache-Control: no-cache to HTML responses. Pure ASGI — no
    BaseHTTPMiddleware scope-copying issues."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                content_type = headers.get(b"content-type", b"").decode("latin-1", errors="ignore")
                if "text/html" in content_type:
                    headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                    headers[b"pragma"] = b"no-cache"
                    headers[b"expires"] = b"0"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ── Pure ASGI Middleware: Auth Guard ─────────────────────────────────────────

PUBLIC_PATHS = {
    "/auth/login",
    "/projects/contract-manager-fresh/auth/login",
    # API auth endpoints (login, but let API routes handle their own auth)
}
STATIC_PREFIXES = ("/static", "/projects/contract-manager-fresh/static")
API_PREFIXES = ("/projects/contract-manager-fresh/api/",)
PUBLIC_API_PATHS = {
    "/projects/contract-manager-fresh/api/auth/login",
}


class AuthGuardMiddleware:
    """Redirect unauthenticated users to login. Pure ASGI — placed inside
    SessionMiddleware so scope['session'] is available.

    Allows all API paths through — API endpoints handle their own auth checks.
    Allows SPA static files through.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Allow public paths
        if path in PUBLIC_PATHS or path in PUBLIC_API_PATHS:
            await self.app(scope, receive, send)
            return

        # Allow static files
        if any(path.startswith(p) for p in STATIC_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Allow all API paths (API endpoints handle their own auth)
        if any(path.startswith(p) for p in API_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Allow SPA static files
        if path.startswith(f"{settings.base_path}/spa/"):
            await self.app(scope, receive, send)
            return

        # Check session (set by SessionMiddleware which wraps this)
        session = scope.get("session", {})
        if not session.get("user_id"):
            # Not logged in — redirect to login
            from starlette.responses import RedirectResponse
            response = RedirectResponse(
                url=f"{settings.base_path}/auth/login",
                status_code=HTTP_302_FOUND,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ── Build middleware stack (innermost → outermost) ───────────────────────────
# Stack order on request: SessionMiddleware → AuthGuard → CacheControl → app
# SessionMiddleware must be outermost so it sets up scope['session'] first.

app.add_middleware(CacheControlMiddleware)
app.add_middleware(AuthGuardMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=False,
)


# ── Templates ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

templates.env.globals["base_path"] = settings.base_path
templates.env.globals["version_token"] = settings.version_token

app.state.templates = templates


# ── Static Files ─────────────────────────────────────────────────────────────

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount(
    f"{settings.base_path}/static",
    StaticFiles(directory=str(static_dir)),
    name="static_prefixed",
)


# ── Route Registration: API (JSON) ───────────────────────────────────────────

app.include_router(api_auth.router, prefix=settings.base_path)
app.include_router(api_contracts.router, prefix=settings.base_path)
app.include_router(api_users.router, prefix=settings.base_path)
app.include_router(api_attachments.router, prefix=settings.base_path)
app.include_router(api_audit.router, prefix=settings.base_path)


# ── Route Registration: SSR (backward-compatible Jinja2) ─────────────────────

app.include_router(auth.router, prefix=settings.base_path)
app.include_router(users.router, prefix=settings.base_path)
app.include_router(contracts.router, prefix=settings.base_path)
app.include_router(attachments.router, prefix=settings.base_path)
app.include_router(attachments.contract_router, prefix=settings.base_path)


# ── SPA Entry Point (root — Vue Router hash mode) ────────────────────────────

SPA_INDEX = BASE_DIR / "static" / "spa" / "index.html"


@app.get(f"{settings.base_path}/", response_class=HTMLResponse)
async def spa_root(request: Request):
    """Serve the Vue SPA index. SPA uses hash routing (/#/login, etc.)."""
    if not SPA_INDEX.exists():
        # Fallback: old dashboard if SPA not built yet
        from app.database import SessionLocal
        from app.services.contract import list_contracts
        from app.models.contract import VALID_STATUSES
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(
                url=f"{settings.base_path}/auth/login",
                status_code=HTTP_302_FOUND,
            )
        db = SessionLocal()
        try:
            contracts = list_contracts(db)
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "contracts": contracts,
                "user": {
                    "user_id": user_id,
                    "username": request.session.get("username"),
                    "role": request.session.get("role"),
                },
                "valid_statuses": VALID_STATUSES,
            })
        finally:
            db.close()
    return FileResponse(SPA_INDEX, media_type="text/html")


# ── Audit Log Viewer (admin only, SSR backward-compatible) ───────────────────

@app.get(f"{settings.base_path}/audit-logs", response_class=HTMLResponse)
async def audit_logs_page(request: Request):
    """View audit logs (admin only) — SSR backward-compatible route."""
    from app.database import SessionLocal
    from app.services.audit import get_audit_logs

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(
            url=f"{settings.base_path}/auth/login",
            status_code=HTTP_302_FOUND,
        )

    if request.session.get("role") != "admin":
        return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    db = SessionLocal()
    try:
        logs = get_audit_logs(db, limit=200)
        return templates.TemplateResponse("audit_logs.html", {
            "request": request,
            "logs": logs,
            "user": {
                "user_id": user_id,
                "username": request.session.get("username"),
                "role": "admin",
            },
        })
    finally:
        db.close()


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """Initialize database tables on first run."""
    init_db()
