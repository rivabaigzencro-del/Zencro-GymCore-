"""Pydantic schemas for Dashboard statistics and aggregated feeds."""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Modular KPI Schemas
# ──────────────────────────────────────────────────────────────────────────────

class MemberStats(BaseModel):
    """Member metrics for dashboard."""
    total_members: int = Field(description="Total registered members in tenant")
    active_members: int = Field(description="Members with ACTIVE status")
    inactive_members: int = Field(description="Members with INACTIVE status")
    expired_memberships: int = Field(description="Members whose latest membership is EXPIRED or have expired memberships")


class FinancialStats(BaseModel):
    """Financial and collection metrics for dashboard."""
    total_revenue_paise: int = Field(description="All-time net collected revenue in paise")
    total_revenue_rupees: float = Field(description="All-time net revenue in rupees")
    today_collection_paise: int = Field(description="Net collection today in paise")
    today_collection_rupees: float = Field(description="Net collection today in rupees")
    monthly_collection_paise: int = Field(description="Net collection this calendar month in paise")
    monthly_collection_rupees: float = Field(description="Net collection this calendar month in rupees")
    pending_payments_count: int = Field(description="Count of unpaid, partially paid or overdue invoices")
    outstanding_dues_paise: int = Field(description="Sum of balance_amount_paise for pending invoices")
    outstanding_dues_rupees: float = Field(description="Sum of balance amounts in rupees")


class MembershipStats(BaseModel):
    """Membership subscription metrics for dashboard."""
    active_memberships: int = Field(description="Currently active subscriptions")
    expired_memberships: int = Field(description="Expired subscriptions")
    expiring_this_week: int = Field(description="Active subscriptions ending within the next 7 days")
    upcoming_renewals: int = Field(description="Active subscriptions ending within the next 30 days")


class AttendanceDailyTrend(BaseModel):
    """Single day check-in count for attendance trends."""
    date: date
    day_name: str
    check_ins: int


class AttendanceStats(BaseModel):
    """Attendance metrics and trend for dashboard."""
    today_check_ins: int = Field(description="Total check-ins recorded today")
    monthly_attendance: int = Field(description="Total check-ins recorded this calendar month")
    daily_trends: List[AttendanceDailyTrend] = Field(description="Recent daily check-in counts")


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Feed Item Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RecentPaymentItem(BaseModel):
    """Recent payment item for dashboard activity feed."""
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


class UpcomingRenewalItem(BaseModel):
    """Upcoming membership renewal item."""
    membership_id: UUID
    member_id: UUID
    member_name: str
    phone: Optional[str] = None
    plan_name: str
    end_date: date
    days_remaining: int


class PendingDueItem(BaseModel):
    """Pending invoice dues item."""
    invoice_id: UUID
    invoice_number: str
    member_id: UUID
    member_name: str
    phone: Optional[str] = None
    due_date: date
    total_amount_paise: int
    balance_amount_paise: int
    balance_amount_rupees: float
    days_overdue: int


class RecentRegistrationItem(BaseModel):
    """Recent member registration item."""
    member_id: UUID
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str
    created_at: datetime


class RecentAttendanceItem(BaseModel):
    """Recent attendance check-in item."""
    attendance_id: UUID
    member_id: UUID
    member_name: str
    phone: Optional[str] = None
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    check_in_method: str
    override_reason: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Aggregated Dashboard Summary
# ──────────────────────────────────────────────────────────────────────────────

class DashboardSummaryResponse(BaseModel):
    """Comprehensive aggregated dashboard summary response."""
    tenant_id: UUID
    as_of: datetime
    member_stats: MemberStats
    financial_stats: FinancialStats
    membership_stats: MembershipStats
    attendance_stats: AttendanceStats
    recent_payments: List[RecentPaymentItem]
    upcoming_renewals: List[UpcomingRenewalItem]
    pending_dues: List[PendingDueItem]
    recent_registrations: List[RecentRegistrationItem]
    recent_attendance: List[RecentAttendanceItem]

