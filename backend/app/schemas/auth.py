import re
from typing import Annotated, Literal

from datetime import datetime

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

EmailAddress = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=254),
]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    email: EmailAddress
    password: Password

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class LoginRequest(BaseModel):
    email: EmailAddress
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailAddress

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Annotated[str, StringConstraints(min_length=32, max_length=256)]
    new_password: Password


class MessageResponse(BaseModel):
    message: str


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: Literal["user", "admin"]
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    user: PublicUser
    message: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
    ] = None
    email: EmailAddress | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("full_name", "email")
    @classmethod
    def reject_null_updates(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Profile fields cannot be null.")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    new_password: Password

    @field_validator("new_password")
    @classmethod
    def ensure_new_password_differs(cls, value: str, info) -> str:
        if value == info.data.get("current_password"):
            raise ValueError("The new password must differ from the current password.")
        return value


class CsrfResponse(BaseModel):
    csrf_token: str
