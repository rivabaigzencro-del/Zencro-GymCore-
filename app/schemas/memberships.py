"""Pydantic schemas for Membership lifecycle operations."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from app.models.membership import MembershipStatus
from app.schemas.members import MemberResponse
from app.schemas.membership_plans import MembershipPlanResponse


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MembershipCreateRequest(BaseModel):
    """Payload to assign a membership plan to a member."""
    member_id: UUID = Field(..., description="Member UUID to assign the membership to")
    membership_plan_id: UUID = Field(..., description="Membership plan UUID to apply")
    start_date: date = Field(..., description="Membership start date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class MembershipFreezeRequest(BaseModel):
    """Payload to freeze an active membership."""
    freeze_start_date: date = Field(..., description="Freeze start date (YYYY-MM-DD)")
    freeze_end_date: date = Field(..., description="Freeze end date (YYYY-MM-DD)")

    @model_validator(mode="after")
    def validate_freeze_dates(self) -> "MembershipFreezeRequest":
        if self.freeze_end_date <= self.freeze_start_date:
            raise ValueError("freeze_end_date must be after freeze_start_date")
        return self


class MembershipUnfreezeRequest(BaseModel):
    """Payload to unfreeze a frozen membership (optional early unfreeze date)."""
    unfreeze_date: Optional[date] = Field(
        None,
        description="Date to unfreeze from (defaults to today if not provided)",
    )


class MembershipRenewRequest(BaseModel):
    """Payload to renew a membership (optionally with a different plan)."""
    membership_plan_id: Optional[UUID] = Field(
        None,
        description="New plan UUID (uses existing plan if not provided)",
    )
    start_date: Optional[date] = Field(
        None,
        description="Renewal start date (defaults to day after current end_date)",
    )
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class MembershipUpgradeRequest(BaseModel):
    """Payload to upgrade or downgrade a membership to a different plan."""
    new_membership_plan_id: UUID = Field(..., description="New plan UUID")
    effective_date: Optional[date] = Field(
        None,
        description="Date change takes effect (defaults to today)",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Reason for change")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MembershipResponse(BaseModel):
    """Full membership details returned by the API."""
    id: UUID
    tenant_id: UUID
    member_id: UUID
    membership_plan_id: UUID
    start_date: date
    end_date: date
    status: MembershipStatus
    freeze_start_date: Optional[date] = None
    freeze_end_date: Optional[date] = None
    total_frozen_days: int
    renewed_from_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Nested detail (populated when joining)
    member: Optional[MemberResponse] = None
    membership_plan: Optional[MembershipPlanResponse] = None

    model_config = ConfigDict(from_attributes=True)


class MembershipListResponse(BaseModel):
    """Paginated list of memberships."""
    items: list[MembershipResponse]
    total: int
    page: int
    page_size: int
    pages: int

