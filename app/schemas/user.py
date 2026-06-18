"""Pydantic schemas for user operations."""

from datetime import datetime
from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=64)
    password: str | None = Field(None, min_length=1, max_length=128)
    role: str | None = Field(None, pattern="^(admin|user)$")


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
