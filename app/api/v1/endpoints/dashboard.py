"""Dashboard REST API endpoints — statistics, KPIs, and aggregated gym feeds."""
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    MemberStats,
    FinancialStats,
    MembershipStats,
    AttendanceStats,
    RecentPaymentItem,
    UpcomingRenewalItem,
    PendingDueItem,
    RecentRegistrationItem,
    RecentAttendanceItem,
    DashboardSummaryResponse,
)
from app.services import dashboard_service

router = APIRouter()

# Staff and management roles authorized to access dashboard data
_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Aggregated Dashboard Summary",
    description="Retrieve all member, financial, membership, and attendance KPIs along with recent feeds.",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> DashboardSummaryResponse:
    return dashboard_service.get_dashboard_summary(db, current_user.tenant_id)


@router.get(
    "/members",
    response_model=MemberStats,
    status_code=status.HTTP_200_OK,
    summary="Member Statistics",
    description="Retrieve member counts: total, active, inactive, and expired memberships.",
)
def get_member_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MemberStats:
    return dashboard_service.get_member_stats(db, current_user.tenant_id)


@router.get(
    "/financial",
    response_model=FinancialStats,
    status_code=status.HTTP_200_OK,
    summary="Financial Statistics",
    description="Retrieve net collection revenue (all-time, today, monthly) and pending dues in paise and rupees.",
)
def get_financial_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> FinancialStats:
    return dashboard_service.get_financial_stats(db, current_user.tenant_id)


@router.get(
    "/memberships",
    response_model=MembershipStats,
    status_code=status.HTTP_200_OK,
    summary="Membership Statistics",
    description="Retrieve membership subscription KPIs: active, expired, expiring this week, and upcoming renewals.",
)
def get_membership_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MembershipStats:
    return dashboard_service.get_membership_stats(db, current_user.tenant_id)


@router.get(
    "/attendance",
    response_model=AttendanceStats,
    status_code=status.HTTP_200_OK,
    summary="Attendance Statistics & Trends",
    description="Retrieve today's check-ins, monthly attendance, and 7-day daily check-in trend.",
)
def get_attendance_stats(
    days_trend: int = Query(7, ge=1, le=30, description="Number of historical days for attendance trend"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> AttendanceStats:
    return dashboard_service.get_attendance_stats(db, current_user.tenant_id, days_trend=days_trend)


@router.get(
    "/recent-payments",
    response_model=List[RecentPaymentItem],
    status_code=status.HTTP_200_OK,
    summary="Recent Payments Feed",
    description="Retrieve the latest completed payment transactions.",
)
def get_recent_payments(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> List[RecentPaymentItem]:
    return dashboard_service.get_recent_payments(db, current_user.tenant_id, limit=limit)


@router.get(
    "/upcoming-renewals",
    response_model=List[UpcomingRenewalItem],
    status_code=status.HTTP_200_OK,
    summary="Upcoming Renewals Feed",
    description="Retrieve active memberships closest to expiration date.",
)
def get_upcoming_renewals(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> List[UpcomingRenewalItem]:
    return dashboard_service.get_upcoming_renewals(db, current_user.tenant_id, limit=limit)


@router.get(
    "/pending-dues",
    response_model=List[PendingDueItem],
    status_code=status.HTTP_200_OK,
    summary="Pending Dues Feed",
    description="Retrieve pending invoices with highest outstanding balances.",
)
def get_pending_dues(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> List[PendingDueItem]:
    return dashboard_service.get_pending_dues(db, current_user.tenant_id, limit=limit)


@router.get(
    "/recent-registrations",
    response_model=List[RecentRegistrationItem],
    status_code=status.HTTP_200_OK,
    summary="Recent Registrations Feed",
    description="Retrieve the most recently registered gym members.",
)
def get_recent_registrations(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> List[RecentRegistrationItem]:
    return dashboard_service.get_recent_registrations(db, current_user.tenant_id, limit=limit)


@router.get(
    "/recent-attendance",
    response_model=List[RecentAttendanceItem],
    status_code=status.HTTP_200_OK,
    summary="Recent Attendance Feed",
    description="Retrieve the latest gym check-in visits.",
)
def get_recent_attendance(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> List[RecentAttendanceItem]:
    return dashboard_service.get_recent_attendance(db, current_user.tenant_id, limit=limit)

