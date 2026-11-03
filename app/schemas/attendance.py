"""Pydantic schemas for Attendance, Check-in/Check-out, QR Validation, Overrides, and Analytics."""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.attendance import CheckInMethod
from app.models.member import MemberStatus


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class CheckInRequest(BaseModel):
    """Payload to perform manual member check-in."""
    member_id: UUID = Field(..., description="Target gym member UUID")
    override: bool = Field(False, description="Set to True if performing an authorized override")
    override_reason: Optional[str] = Field(None, max_length=500, description="Mandatory audit reason if override is True")

    @field_validator("override_reason")
    @classmethod
    def clean_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class QRCheckInRequest(BaseModel):
    """Payload to validate and check in via member's secure QR code."""
    qr_code: str = Field(..., min_length=10, max_length=64, description="Opaque QR identifier")
    override: bool = Field(False, description="Set to True if performing an authorized override")
    override_reason: Optional[str] = Field(None, max_length=500, description="Mandatory audit reason if override is True")

    @field_validator("qr_code", "override_reason")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class CheckOutRequest(BaseModel):
    """Payload to check out an active visit."""
    notes: Optional[str] = Field(None, max_length=500, description="Optional check-out notes")


class AttendanceSettingsUpdateRequest(BaseModel):
    """Payload to update gym-level check-in policies."""
    attendance_block_expired: Optional[bool] = Field(None, description="Block expired memberships")
    attendance_allow_override: Optional[bool] = Field(None, description="Allow staff overrides with reason")
    attendance_block_on_dues: Optional[bool] = Field(None, description="Block check-in if member has overdue invoices")


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class EligibilityResponse(BaseModel):
    """Structured membership eligibility analysis for check-in."""
    eligible: bool
    member_id: UUID
    member_name: str
    membership_id: Optional[UUID] = None
    membership_status: str  # ACTIVE, EXPIRING, EXPIRED, FROZEN, CANCELLED, NONE, FUTURE
    plan_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    warning: Optional[str] = None
    override_permitted: bool = False
    has_outstanding_dues: bool = False
    outstanding_dues_paise: int = 0


class MemberSearchResult(BaseModel):
    """Member search item for fast receptionist check-in desk."""
    member_id: UUID
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    member_code: Optional[str] = None
    qr_code: Optional[str] = None
    member_status: MemberStatus
    active_membership_status: Optional[str] = None
    plan_name: Optional[str] = None
    membership_end_date: Optional[date] = None
    is_currently_checked_in: bool = False
    active_attendance_id: Optional[UUID] = None


class MemberQRResponse(BaseModel):
    """Member QR identification details."""
    member_id: UUID
    member_name: str
    member_code: Optional[str] = None
    qr_code: str


class AttendanceResponse(BaseModel):
    """Full attendance record returned by the API."""
    id: UUID
    tenant_id: UUID
    member_id: UUID
    member_name: Optional[str] = None
    member_phone: Optional[str] = None
    member_code: Optional[str] = None
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    check_in_method: CheckInMethod
    checked_in_by_id: Optional[UUID] = None
    checked_in_by_name: Optional[str] = None
    checked_out_by_id: Optional[UUID] = None
    is_override: bool
    override_reason: Optional[str] = None
    override_by_id: Optional[UUID] = None
    is_active: bool
    duration_minutes: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceListResponse(BaseModel):
    """Paginated list of attendance entries."""
    items: List[AttendanceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AttendanceSummaryResponse(BaseModel):
    """Daily attendance metrics summary."""
    tenant_id: UUID
    date: date
    total_check_ins: int
    unique_members: int
    active_check_ins: int
    completed_visits: int


class PeakHoursResponse(BaseModel):
    """Hourly attendance aggregation for capacity and peak-hour planning."""
    tenant_id: UUID
    from_date: date
    to_date: date
    hourly_breakdown: List[Dict[str, Any]]
    peak_hour: Optional[int] = None
    peak_hour_label: Optional[str] = None
    peak_hour_count: int = 0


class AttendanceFrequencyResponse(BaseModel):
    """Member visit frequency analytics."""
    tenant_id: UUID
    from_date: date
    to_date: date
    total_visits: int
    unique_members: int
    top_members: List[Dict[str, Any]]
    frequency_distribution: Dict[str, int]


class AttendanceSettingsResponse(BaseModel):
    """Gym-level attendance and check-in configuration."""
    tenant_id: UUID
    attendance_block_expired: bool
    attendance_allow_override: bool
    attendance_block_on_dues: bool

