"""Pydantic schemas for MembershipPlan CRUD operations."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.membership_plan import DurationUnit


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MembershipPlanCreateRequest(BaseModel):
    """Payload to create a new membership plan."""
    name: str = Field(..., min_length=2, max_length=255, description="Plan display name")
    description: Optional[str] = Field(None, description="Plan description")
    duration: int = Field(..., gt=0, le=3650, description="Duration quantity (must be positive, max 3650)")
    duration_unit: DurationUnit = Field(DurationUnit.MONTHS, description="DAYS or MONTHS")
    price: Decimal = Field(..., ge=0, le=99999999.99, description="Price in INR (must be non-negative, max 99,999,999.99)")
    is_active: bool = Field(True, description="Whether plan is active and available")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Plan name must contain at least 2 non-whitespace characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price cannot be negative")
        if v > Decimal("99999999.99"):
            raise ValueError("Price exceeds maximum permitted limit")
        # Round to 2 decimal places
        return round(v, 2)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duration must be a positive integer")
        if v > 3650:
            raise ValueError("Duration cannot exceed 3650 days/months")
        return v


class MembershipPlanUpdateRequest(BaseModel):
    """Payload to update an existing membership plan."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    duration: Optional[int] = Field(None, gt=0, le=3650)
    duration_unit: Optional[DurationUnit] = None
    price: Optional[Decimal] = Field(None, ge=0, le=99999999.99)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Plan name cannot be null")
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Plan name must contain at least 2 non-whitespace characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            raise ValueError("Price cannot be null")
        if v < 0:
            raise ValueError("Price cannot be negative")
        if v > Decimal("99999999.99"):
            raise ValueError("Price exceeds maximum permitted limit")
        return round(v, 2)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            raise ValueError("Duration cannot be null")
        if v <= 0:
            raise ValueError("Duration must be a positive integer")
        if v > 3650:
            raise ValueError("Duration cannot exceed 3650")
        return v

    @field_validator("duration_unit")
    @classmethod
    def validate_duration_unit(cls, v: Optional[DurationUnit]) -> Optional[DurationUnit]:
        if v is None:
            raise ValueError("Duration unit cannot be null")
        return v

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v: Optional[bool]) -> Optional[bool]:
        if v is None:
            raise ValueError("is_active cannot be null")
        return v


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MembershipPlanResponse(BaseModel):
    """Membership plan details returned by the API."""
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    duration: int
    duration_unit: DurationUnit
    price: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipPlanListResponse(BaseModel):
    """List of membership plans."""
    items: list[MembershipPlanResponse]
    total: int

