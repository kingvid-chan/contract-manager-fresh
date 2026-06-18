"""Contracts API — JSON CRUD and status management."""

from datetime import date
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.contract import (
    list_contracts, get_contract_by_id, create_contract,
    update_contract, change_status, delete_contract,
)
from app.models.contract import VALID_STATUSES, STATUS_FLOW

router = APIRouter(prefix="/api/contracts", tags=["api-contracts"])


def _get_user(request: Request):
    return {
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


def _contract_to_dict(c) -> dict:
    return {
        "id": c.id,
        "contract_no": c.contract_no,
        "title": c.title,
        "party_a": c.party_a,
        "party_b": c.party_b,
        "sign_date": c.sign_date.isoformat() if c.sign_date else None,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
        "amount": float(c.amount) if c.amount else None,
        "status": c.status,
        "remarks": c.remarks,
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "creator_name": c.creator.username if c.creator else "",
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "file_size": a.file_size,
                "mime_type": a.mime_type,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in (c.attachments or [])
        ],
        "valid_transitions": STATUS_FLOW.get(c.status, []),
    }


class ContractCreate(BaseModel):
    title: str
    party_a: str
    party_b: str = ""
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    amount: float | None = None
    remarks: str | None = None


class ContractUpdate(BaseModel):
    title: str
    party_a: str
    party_b: str = ""
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    amount: float | None = None
    remarks: str | None = None


class StatusChange(BaseModel):
    status: str


def _parse_date(s: str | None) -> date | None:
    if s and s.strip():
        return date.fromisoformat(s.strip())
    return None


@router.get("")
async def api_list_contracts(request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    contracts = list_contracts(db)
    return {"ok": True, "contracts": [_contract_to_dict(c) for c in contracts]}


@router.get("/{contract_id}")
async def api_get_contract(contract_id: int, request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    c = get_contract_by_id(db, contract_id)
    if not c:
        return {"ok": False, "error": "合同不存在"}
    return {"ok": True, "contract": _contract_to_dict(c)}


@router.post("")
async def api_create_contract(body: ContractCreate, request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    if not body.title.strip():
        return {"ok": False, "error": "合同名称不能为空"}
    if not body.party_a.strip():
        return {"ok": False, "error": "甲方不能为空"}
    data = {
        "title": body.title,
        "party_a": body.party_a,
        "party_b": body.party_b,
        "sign_date": _parse_date(body.sign_date),
        "start_date": _parse_date(body.start_date),
        "end_date": _parse_date(body.end_date),
        "amount": body.amount,
        "remarks": body.remarks,
    }
    c = create_contract(db, data, u["user_id"])
    return {"ok": True, "contract": _contract_to_dict(c)}


@router.put("/{contract_id}")
async def api_update_contract(
    contract_id: int, body: ContractUpdate, request: Request, db: Session = Depends(get_db)
):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    c = get_contract_by_id(db, contract_id)
    if not c:
        return {"ok": False, "error": "合同不存在"}
    data = {
        "title": body.title,
        "party_a": body.party_a,
        "party_b": body.party_b,
        "sign_date": _parse_date(body.sign_date),
        "start_date": _parse_date(body.start_date),
        "end_date": _parse_date(body.end_date),
        "amount": body.amount,
        "remarks": body.remarks,
    }
    update_contract(db, c, data, u["user_id"])
    return {"ok": True, "contract": _contract_to_dict(c)}


@router.post("/{contract_id}/status")
async def api_change_status(
    contract_id: int, body: StatusChange, request: Request, db: Session = Depends(get_db)
):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    c = get_contract_by_id(db, contract_id)
    if not c:
        return {"ok": False, "error": "合同不存在"}
    try:
        change_status(db, c, body.status, u["user_id"])
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "contract": _contract_to_dict(c)}


@router.delete("/{contract_id}")
async def api_delete_contract(contract_id: int, request: Request, db: Session = Depends(get_db)):
    u = _get_user(request)
    if not u["user_id"]:
        return {"ok": False, "error": "未登录"}
    c = get_contract_by_id(db, contract_id)
    if not c:
        return {"ok": False, "error": "合同不存在"}
    delete_contract(db, c, u["user_id"])
    return {"ok": True}
