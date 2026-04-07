"""User model."""
from __future__ import annotations
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


UserStatus = Literal["active", "banned", "pending"]
UserRole = Literal["user", "admin"]


class UserInDB(BaseModel):
    """User document stored in MongoDB."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password_hash: str
    role: UserRole = "user"
    status: UserStatus = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class UserPublic(BaseModel):
    """User info safe to return in API responses (no password)."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime] = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = Field(default=None, max_length=254)
    full_name: Optional[str] = Field(default=None, max_length=100)


class UpdateUserStatusRequest(BaseModel):
    status: UserStatus


class UpdateUserRoleRequest(BaseModel):
    role: UserRole
