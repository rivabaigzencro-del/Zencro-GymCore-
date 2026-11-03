"""Reports REST API endpoints — analytics, revenue summaries, and operational reports."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.reports import (
    RevenueReportResponse,
    MembershipReportResponse,
    AttendanceReportResponse,
    PendingDuesReportResponse,
    ExpiryReportResponse,
)
from app.services import report_service

router = APIRouter()

# Financial report permissions (sensitive revenue figures)
_FINANCIAL_ROLES = (UserRole.OWNER, UserRole.MANAGER)
# Operational report permissions
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)


@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Revenue and Collection Report",
    description="Generate detailed revenue report within a date range, broken down by payment methods with net collection totals.",
)
def get_revenue_report(
    start_date: Optional[date] = Query(None, description="Start date (default: first day of current month)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    payment_method: Optional[str] = Query(None, description="Filter by method: CASH, UPI, CARD, BANK_TRANSFER, CHEQUE"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_FINANCIAL_ROLES)),
) -> RevenueReportResponse:
    today = date.today()
    sd = start_date or today.replace(day=1)
    ed = end_date or today
    return report_service.generate_revenue_report(
        db,
        current_user.tenant_id,
        start_date=sd,
        end_date=ed,
        payment_method=payment_method,
    )


@router.get(
    "/memberships",
    response_model=MembershipReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Membership Report",
    description="Generate membership report with status distributions, plan breakdowns, and subscription records.",
)
def get_membership_report(
    start_date: Optional[date] = Query(None, description="Filter memberships starting on or after date"),
    end_date: Optional[date] = Query(None, description="Filter memberships starting on or before date"),
    plan_id: Optional[UUID] = Query(None, description="Filter by specific membership plan UUID"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, EXPIRED, FROZEN, CANCELLED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipReportResponse:
    return report_service.generate_membership_report(
        db,
        current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        plan_id=plan_id,
        status_filter=status,
    )


@router.get(
    "/attendance",
    response_model=AttendanceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Attendance Report",
    description="Generate gym check-in report with peak hours distribution, unique attendees, and visit records.",
)
def get_attendance_report(
    start_date: Optional[date] = Query(None, description="Start date (default: first day of current month)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    member_id: Optional[UUID] = Query(None, description="Filter visits for a single member"),
    check_in_method: Optional[str] = Query(None, description="Filter by method: MANUAL, QR"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> AttendanceReportResponse:
    today = date.today()
    sd = start_date or today.replace(day=1)
    ed = end_date or today
    return report_service.generate_attendance_report(
        db,
        current_user.tenant_id,
        start_date=sd,
        end_date=ed,
        member_id=member_id,
        check_in_method=check_in_method,
    )


@router.get(
    "/pending-dues",
    response_model=PendingDuesReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Pending Dues and Billing Report",
    description="Generate overdue and unpaid billing report with ageing buckets (0-7, 8-30, 30+ days).",
)
def get_pending_dues_report(
    ageing_bucket: Optional[str] = Query(None, description="Filter by bucket: '0-7', '8-30', '30+', 'current'"),
    status: Optional[str] = Query(None, description="Filter by invoice status: UNPAID, PARTIALLY_PAID, OVERDUE"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_FINANCIAL_ROLES)),
) -> PendingDuesReportResponse:
    return report_service.generate_pending_dues_report(
        db,
        current_user.tenant_id,
        ageing_bucket=ageing_bucket,
        status_filter=status,
    )


@router.get(
    "/expiries",
    response_model=ExpiryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Membership Expiry and Renewal Report",
    description="Generate membership expiry report categorized into EXPIRING_SOON, EXPIRING_TODAY, EXPIRED, and LAPSED.",
)
def get_expiry_report(
    start_date: Optional[date] = Query(None, description="Filter memberships expiring on or after date"),
    end_date: Optional[date] = Query(None, description="Filter memberships expiring on or before date"),
    status: Optional[str] = Query(None, description="Filter by category: EXPIRING_SOON, EXPIRING_TODAY, EXPIRED, LAPSED, ALL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ExpiryReportResponse:
    return report_service.generate_expiry_report(
        db,
        current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        status_filter=status,
    )

