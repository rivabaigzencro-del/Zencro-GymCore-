"""Pydantic schemas for Member CRUD operations."""
import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.member import MemberStatus, Gender


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MemberCreateRequest(BaseModel):
    """Payload to register a new gym member."""
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of the member")
    email: Optional[str] = Field(None, max_length=255, description="Member email address")
    phone: Optional[str] = Field(None, max_length=50, description="Primary contact phone")
    gender: Optional[Gender] = Field(None, description="Member gender")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")
    address: Optional[str] = Field(None, description="Residential address")
    emergency_contact_name: Optional[str] = Field(None, max_length=255, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, max_length=50, description="Emergency contact phone")
    status: MemberStatus = Field(MemberStatus.ACTIVE, description="Initial member status")

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: MemberStatus) -> MemberStatus:
        if v != MemberStatus.ACTIVE:
            raise ValueError("Initial member status must be ACTIVE; other statuses are system-managed")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must contain at least 2 non-whitespace characters")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        if not re.match(r"^[\w\.\+\-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\+?[\d\s\-\(\)]{6,20}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("emergency_contact_name")
    @classmethod
    def validate_emergency_contact_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\+?[\d\s\-\(\)]{6,20}$", v):
            raise ValueError("Invalid emergency contact phone number format")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class MemberUpdateRequest(BaseModel):
    """Payload to update an existing gym member's information."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    status: Optional[MemberStatus] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[MemberStatus]) -> Optional[MemberStatus]:
        if v is not None:
            raise ValueError("Member lifecycle status cannot be directly modified by clients")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Full name cannot be null")
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must contain at least 2 non-whitespace characters")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        if not re.match(r"^[\w\.\+\-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\+?[\d\s\-\(\)]{6,20}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @field_validator("emergency_contact_name")
    @classmethod
    def validate_emergency_contact_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\+?[\d\s\-\(\)]{6,20}$", v):
            raise ValueError("Invalid emergency contact phone number format")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MemberResponse(BaseModel):
    """Safe public member information returned by the API."""
    id: UUID
    tenant_id: UUID
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberListResponse(BaseModel):
    """Paginated list of members."""
    items: list[MemberResponse]
    total: int
    page: int
    page_size: int
    pages: int

