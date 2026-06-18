"""Contract routes — CRUD and status management."""

from datetime import date
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_db
from app.services.contract import (
    list_contracts, get_contract_by_id, create_contract,
    update_contract, change_status, delete_contract,
)
from app.models.contract import VALID_STATUSES
from app.config import settings

router = APIRouter(prefix="/contracts", tags=["contracts"])


def get_session_user(request: Request) -> dict:
    """Extract user info from session. Returns empty dict if not logged in."""
    return {
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


@router.get("")
async def contract_list(request: Request, db: Session = Depends(get_db)):
    """List all contracts (authenticated users)."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contracts = list_contracts(db)
    return tmpl.TemplateResponse("contracts/list.html", {
        "request": request,
        "contracts": contracts,
        "user": user,
        "valid_statuses": VALID_STATUSES,
    })


@router.get("/new")
async def contract_create_form(request: Request):
    """Show create-contract form."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)
    return tmpl.TemplateResponse("contracts/edit.html", {
        "request": request,
        "contract": None,
        "user": user,
    })


@router.post("")
async def contract_create(
    request: Request,
    title: str = Form(...),
    party_a: str = Form(...),
    party_b: str = Form(""),
    sign_date: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    amount: float | None = Form(None),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Create a new contract."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    def parse_date(s: str | None) -> date | None:
        if s and s.strip():
            return date.fromisoformat(s.strip())
        return None

    data = {
        "title": title,
        "party_a": party_a,
        "party_b": party_b,
        "sign_date": parse_date(sign_date),
        "start_date": parse_date(start_date),
        "end_date": parse_date(end_date),
        "amount": amount,
        "remarks": remarks,
    }

    error = None
    if not title.strip():
        error = "合同名称不能为空"
    if not party_a.strip():
        error = "甲方不能为空"

    if error:
        return tmpl.TemplateResponse("contracts/edit.html", {
            "request": request, "contract": None, "user": user, "error": error,
        }, status_code=400)

    contract = create_contract(db, data, user["user_id"])
    return RedirectResponse(
        url=f"{settings.base_path}/contracts/{contract.id}",
        status_code=HTTP_302_FOUND,
    )


@router.get("/{contract_id}")
async def contract_detail(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """Show contract detail with attachments."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = get_contract_by_id(db, contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    return tmpl.TemplateResponse("contracts/detail.html", {
        "request": request,
        "contract": contract,
        "user": user,
        "valid_statuses": VALID_STATUSES,
    })


@router.get("/{contract_id}/edit")
async def contract_edit_form(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """Show edit-contract form."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = get_contract_by_id(db, contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    return tmpl.TemplateResponse("contracts/edit.html", {
        "request": request,
        "contract": contract,
        "user": user,
    })


@router.post("/{contract_id}/edit")
async def contract_edit(
    request: Request,
    contract_id: int,
    title: str = Form(...),
    party_a: str = Form(...),
    party_b: str = Form(""),
    sign_date: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    amount: float | None = Form(None),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Update a contract."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = get_contract_by_id(db, contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    def parse_date(s: str | None) -> date | None:
        if s and s.strip():
            return date.fromisoformat(s.strip())
        return None

    data = {
        "title": title,
        "party_a": party_a,
        "party_b": party_b,
        "sign_date": parse_date(sign_date),
        "start_date": parse_date(start_date),
        "end_date": parse_date(end_date),
        "amount": amount,
        "remarks": remarks,
    }

    update_contract(db, contract, data, user["user_id"])
    return RedirectResponse(
        url=f"{settings.base_path}/contracts/{contract_id}",
        status_code=HTTP_302_FOUND,
    )


@router.post("/{contract_id}/status")
async def contract_change_status(
    request: Request,
    contract_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    """Change contract status."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = get_contract_by_id(db, contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    try:
        change_status(db, contract, status, user["user_id"])
    except ValueError as e:
        return tmpl.TemplateResponse("contracts/detail.html", {
            "request": request, "contract": contract, "user": user,
            "error": str(e), "valid_statuses": VALID_STATUSES,
        }, status_code=400)

    return RedirectResponse(
        url=f"{settings.base_path}/contracts/{contract_id}",
        status_code=HTTP_302_FOUND,
    )


@router.post("/{contract_id}/delete")
async def contract_delete(request: Request, contract_id: int, db: Session = Depends(get_db)):
    """Delete a contract."""
    tmpl = request.app.state.templates
    user = get_session_user(request)
    if not user["user_id"]:
        return RedirectResponse(url=f"{settings.base_path}/auth/login", status_code=HTTP_302_FOUND)

    contract = get_contract_by_id(db, contract_id)
    if not contract:
        return tmpl.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

    delete_contract(db, contract, user["user_id"])
    return RedirectResponse(url=f"{settings.base_path}/", status_code=HTTP_302_FOUND)
