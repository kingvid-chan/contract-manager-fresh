"""Contract service — business logic for contract CRUD and status flow."""

from datetime import date, datetime
from sqlalchemy.orm import Session

from app.models.contract import Contract, VALID_STATUSES, STATUS_FLOW
from app.services.audit import log_action


def generate_contract_no(db: Session) -> str:
    """Generate a unique contract number: C-YYYYMMDD-NNN.

    Finds the maximum existing suffix for today's date and increments,
    handling gaps from deleted contracts correctly.
    """
    today = date.today().strftime("%Y%m%d")
    prefix = f"C-{today}-"
    # Find the highest existing suffix for today
    existing = (
        db.query(Contract.contract_no)
        .filter(Contract.contract_no.like(f"{prefix}%"))
        .order_by(Contract.contract_no.desc())
        .first()
    )
    if existing and existing[0]:
        # Extract numeric suffix and increment
        try:
            last_num = int(existing[0].split("-")[-1])
        except (ValueError, IndexError):
            last_num = 0
    else:
        last_num = 0
    return f"{prefix}{last_num + 1:03d}"


def list_contracts(db: Session) -> list[Contract]:
    """Return all contracts, newest first."""
    return db.query(Contract).order_by(Contract.created_at.desc()).all()


def get_contract_by_id(db: Session, contract_id: int) -> Contract | None:
    return db.query(Contract).get(contract_id)


def get_contract_by_no(db: Session, contract_no: str) -> Contract | None:
    return db.query(Contract).filter(Contract.contract_no == contract_no).first()


def create_contract(db: Session, data: dict, user_id: int) -> Contract:
    """Create a new contract with auto-generated number."""
    contract = Contract(
        contract_no=generate_contract_no(db),
        title=data["title"],
        party_a=data["party_a"],
        party_b=data.get("party_b", ""),
        sign_date=data.get("sign_date"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        amount=data.get("amount"),
        status="draft",
        remarks=data.get("remarks"),
        created_by=user_id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    log_action(db, user_id, "create", "contract", contract.id, {"contract_no": contract.contract_no})
    return contract


def update_contract(db: Session, contract: Contract, data: dict, user_id: int) -> Contract:
    """Update mutable fields of a contract."""
    updatable = ["title", "party_a", "party_b", "sign_date", "start_date",
                  "end_date", "amount", "remarks"]
    changes = {}
    for field in updatable:
        if field in data and data[field] is not None:
            old = getattr(contract, field, None)
            new = data[field]
            if old != new:
                changes[field] = {"old": str(old), "new": str(new)}
            setattr(contract, field, data[field])
    db.commit()
    db.refresh(contract)
    if changes:
        log_action(db, user_id, "update", "contract", contract.id, changes)
    return contract


def change_status(db: Session, contract: Contract, target_status: str, user_id: int) -> Contract:
    """Transition contract to target_status, validating the state machine."""
    if target_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {target_status}")
    if not contract.can_transition_to(target_status):
        raise ValueError(
            f"Cannot transition from {contract.status} to {target_status}. "
            f"Allowed: {STATUS_FLOW.get(contract.status, [])}"
        )
    old_status = contract.status
    contract.status = target_status
    db.commit()
    db.refresh(contract)
    log_action(
        db, user_id, "update", "contract", contract.id,
        {"status": {"old": old_status, "new": target_status}},
    )
    return contract


def delete_contract(db: Session, contract: Contract, user_id: int) -> None:
    """Delete a contract. Callers must check authorization."""
    log_action(db, user_id, "delete", "contract", contract.id,
               {"contract_no": contract.contract_no})
    db.delete(contract)
    db.commit()
