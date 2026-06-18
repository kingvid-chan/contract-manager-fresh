"""Pydantic schemas for contract operations."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class ContractCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    party_a: str = Field(..., min_length=1, max_length=256)
    party_b: str = Field(default="", max_length=256)
    sign_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = None
    remarks: str | None = None


class ContractUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    party_a: str | None = Field(None, min_length=1, max_length=256)
    party_b: str | None = Field(None, max_length=256)
    sign_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = None
    remarks: str | None = None


class StatusChange(BaseModel):
    status: str = Field(...)


class ContractOut(BaseModel):
    id: int
    contract_no: str
    title: str
    party_a: str
    party_b: str
    sign_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = None
    status: str
    remarks: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
