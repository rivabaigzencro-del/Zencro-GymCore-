"""Pydantic schemas for Staff Management & RBAC."""
import re
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.user import UserRole


class StaffCreateRequest(BaseModel):
    """Payload to create a new staff member (MANAGER or FRONT_DESK)."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name of staff member")
    email: str = Field(..., description="Unique email address")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    password: str = Field(..., min_length=8, description="Initial account password (minimum 8 characters)")
    role: UserRole = Field(..., description="Staff role: MANAGER or FRONT_DESK")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return v

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

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.OWNER:
            raise ValueError("Cannot create an OWNER via staff management. Gym owner is set during registration.")
        return v


class StaffUpdateRequest(BaseModel):
    """Payload to update staff profile information."""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Full name of staff member")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    email: Optional[str] = Field(None, description="Updated email address")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class StaffStatusUpdateRequest(BaseModel):
    """Payload to activate or deactivate a staff member."""
    is_active: bool = Field(..., description="Active status for staff member")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class StaffRoleUpdateRequest(BaseModel):
    """Payload to update a staff member's role (OWNER only)."""
    role: UserRole = Field(..., description="New role for the staff member")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for role change")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.OWNER:
            raise ValueError("Cannot promote staff to OWNER role.")
        return v

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class StaffResponse(BaseModel):
    """Safe representation of a staff member (excludes password hash)."""
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


class StaffListResponse(BaseModel):
    """Paginated list of staff members."""
    items: List[StaffResponse]
    total: int
    page: int
    page_size: int
    pages: int

