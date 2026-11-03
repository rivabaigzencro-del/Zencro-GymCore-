"""Pydantic schemas for Reports endpoints."""
from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# 1. Revenue & Collection Report
# ──────────────────────────────────────────────────────────────────────────────

class RevenuePaymentItem(BaseModel):
    """Transaction item in revenue report."""
    payment_id: UUID
    invoice_number: Optional[str] = None
    member_name: str
    member_id: UUID
    amount_paise: int
    amount_rupees: float
    payment_method: str
    payment_status: str
    payment_date: datetime
    receipt_number: Optional[str] = None


class RevenueReportSummary(BaseModel):
    """Summary metrics for revenue report."""
    total_gross_paise: int
    total_gross_rupees: float
    total_refunds_paise: int
    total_refunds_rupees: float
    total_reversals_paise: int
    total_reversals_rupees: float
    total_net_paise: int
    total_net_rupees: float
    transaction_count: int
    by_payment_method: Dict[str, int] = Field(
        description="Gross collection in paise broken down by payment method"
    )


class RevenueReportResponse(BaseModel):
    """Response model for revenue and collection report."""
    tenant_id: UUID
    start_date: date
    end_date: date
    summary: RevenueReportSummary
    transactions: List[RevenuePaymentItem]


# ──────────────────────────────────────────────────────────────────────────────
# 2. Membership Report
# ──────────────────────────────────────────────────────────────────────────────

class MembershipReportItem(BaseModel):
    """Membership record in membership report."""
    membership_id: UUID
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    plan_name: str
    start_date: date
    end_date: date
    status: str
    price_paise: int
    price_rupees: float


class MembershipReportSummary(BaseModel):
    """Summary metrics for membership report."""
    total_memberships: int
    active_count: int
    expired_count: int
    frozen_count: int
    cancelled_count: int
    by_plan: Dict[str, int] = Field(description="Count of memberships grouped by plan name")


class MembershipReportResponse(BaseModel):
    """Response model for membership report."""
    tenant_id: UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    summary: MembershipReportSummary
    memberships: List[MembershipReportItem]


# ──────────────────────────────────────────────────────────────────────────────
# 3. Attendance Report
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceReportItem(BaseModel):
    """Attendance visit record in attendance report."""
    attendance_id: UUID
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    check_in_method: str
    override_reason: Optional[str] = None


class AttendanceReportSummary(BaseModel):
    """Summary metrics for attendance report."""
    total_visits: int
    unique_members: int
    avg_daily_visits: float
    overridden_visits_count: int
    by_method: Dict[str, int] = Field(description="Visits broken down by check-in method")
    by_time_slot: Dict[str, int] = Field(description="Visits by time slot: Morning, Afternoon, Evening, Night")


class AttendanceReportResponse(BaseModel):
    """Response model for attendance report."""
    tenant_id: UUID
    start_date: date
    end_date: date
    summary: AttendanceReportSummary
    visits: List[AttendanceReportItem]


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pending Dues & Billing Report
# ──────────────────────────────────────────────────────────────────────────────

class PendingDueReportItem(BaseModel):
    """Invoice record with outstanding balance."""
    invoice_id: UUID
    invoice_number: str
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    issue_date: date
    due_date: date
    total_amount_paise: int
    paid_amount_paise: int
    balance_amount_paise: int
    balance_amount_rupees: float
    days_overdue: int
    status: str
    ageing_bucket: str = Field(description="Ageing bucket: '0-7 days', '8-30 days', '30+ days', or 'current'")


class PendingDuesReportSummary(BaseModel):
    """Summary metrics for pending dues report."""
    total_outstanding_paise: int
    total_outstanding_rupees: float
    total_pending_invoices: int
    bucket_0_7_paise: int
    bucket_8_30_paise: int
    bucket_30_plus_paise: int
    bucket_current_paise: int


class PendingDuesReportResponse(BaseModel):
    """Response model for pending dues report."""
    tenant_id: UUID
    summary: PendingDuesReportSummary
    invoices: List[PendingDueReportItem]


# ──────────────────────────────────────────────────────────────────────────────
# 5. Membership Expiry & Renewal Report
# ──────────────────────────────────────────────────────────────────────────────

class ExpiryReportItem(BaseModel):
    """Membership record in expiry and renewal report."""
    membership_id: UUID
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    plan_name: str
    end_date: date
    days_remaining: int
    status: str = Field(description="'EXPIRING_SOON', 'EXPIRING_TODAY', 'EXPIRED', or 'LAPSED'")


class ExpiryReportSummary(BaseModel):
    """Summary metrics for expiry report."""
    total_count: int
    expiring_soon_count: int
    expiring_today_count: int
    expired_count: int
    lapsed_count: int


class ExpiryReportResponse(BaseModel):
    """Response model for expiry report."""
    tenant_id: UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    summary: ExpiryReportSummary
    items: List[ExpiryReportItem]

