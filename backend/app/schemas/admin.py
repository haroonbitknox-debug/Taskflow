import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models import UserRole

AdminEmail = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
AdminPassword = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    email: AdminEmail
    password: AdminPassword
    role: UserRole = UserRole.USER
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=120),
    ] = None
    email: AdminEmail | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("full_name", "email", "role", "is_active")
    @classmethod
    def reject_null_updates(cls, value):
        if value is None:
            raise ValueError("Admin user fields cannot be null.")
        return value


class AdminUserQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Annotated[str | None, StringConstraints(max_length=200)] = None
    role: UserRole | None = None
    is_active: bool | None = None


class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: Literal["user", "admin"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int
