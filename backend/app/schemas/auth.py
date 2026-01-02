"""Authentication schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data schema."""

    teacher_id: Optional[UUID] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Registration request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class TeacherResponse(BaseModel):
    """Teacher response schema."""

    id: UUID
    email: str
    name: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True

