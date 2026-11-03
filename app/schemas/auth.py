import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    """Payload for registering a new gym/tenant and its owner."""
    gym_name: str = Field(..., min_length=2, max_length=255, description="Name of the gym / facility")
    name: str = Field(..., min_length=2, max_length=255, description="Full name of gym owner")
    email: str = Field(..., description="Unique email address for the owner account")
    password: str = Field(..., min_length=8, description="Account password (minimum 8 characters)")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    address: Optional[str] = Field(None, description="Physical gym address")
    timezone: str = Field("Asia/Kolkata", max_length=50, description="Business timezone (default IST)")
    currency: str = Field("INR", max_length=10, description="Operating currency (default INR)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password exceeds maximum bcrypt length of 72 bytes")
        return v


class LoginRequest(BaseModel):
    """Payload for user authentication."""
    email: str = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password exceeds maximum bcrypt length of 72 bytes")
        return v


class UserResponse(BaseModel):
    """Safe public user information (password_hash is excluded)."""
    id: UUID
    tenant_id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantResponse(BaseModel):
    """Safe public tenant information."""
    id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    timezone: str
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    """Response returned upon successful registration."""
    message: str = "Gym and owner registered successfully"
    tenant: TenantResponse
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """JWT access token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
