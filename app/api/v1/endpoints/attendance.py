"""Attendance REST API endpoints."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.auth import require_role
from app.core.database import get_db
from app.models.attendance import CheckInMethod
from app.models.user import User, UserRole
from app.schemas.attendance import (
    CheckInRequest,
    QRCheckInRequest,
    CheckOutRequest,
    AttendanceResponse,
    AttendanceListResponse,
    AttendanceSummaryResponse,
    PeakHoursResponse,
    AttendanceFrequencyResponse,
    AttendanceSettingsUpdateRequest,
    AttendanceSettingsResponse,
    EligibilityResponse,
    MemberSearchResult,
    MemberQRResponse,
)
from app.services import attendance_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_MANAGE_ROLES = (UserRole.OWNER, UserRole.MANAGER)
_ADMIN_ROLES = (UserRole.OWNER,)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Search and Eligibility Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/search-members",
    response_model=list[MemberSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search Members for Check-in Desk",
    description="Fast lookup of members by name, phone, or member code with current membership and check-in indicators.",
)
async def search_members_for_checkin(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=50, description="Max search results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> list[MemberSearchResult]:
    return attendance_service.search_members_for_checkin(
        db=db,
        tenant_id=current_user.tenant_id,
        query_str=q,
        limit=limit,
    )


@router.get(
    "/eligibility/{member_id}",
    response_model=EligibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Membership Eligibility",
    description="Run centralized membership eligibility engine to determine check-in clearance, dues, or override requirements.",
)
async def get_membership_eligibility(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> EligibilityResponse:
    return attendance_service.evaluate_membership_eligibility(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Check-in and Check-out Actions
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/check-in",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manual Member Check-in",
    description="Process manual check-in. If membership is ineligible, requires authorized override flag and reason.",
)
async def check_in_member(
    payload: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> AttendanceResponse:
    attendance = attendance_service.check_in_member(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
        staff_user=current_user,
    )
    return attendance_service._to_attendance_response(attendance)


@router.post(
    "/qr-check-in",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="QR Code Member Check-in",
    description="Validate secure QR code and record QR check-in after membership eligibility verification.",
)
async def qr_check_in(
    payload: QRCheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> AttendanceResponse:
    attendance = attendance_service.qr_check_in(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
        staff_user=current_user,
    )
    return attendance_service._to_attendance_response(attendance)


@router.post(
    "/members/{member_id}/check-out",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Out Member Active Visit",
    description="Locate member's currently active check-in visit and record check-out.",
)
async def check_out_member_active(
    member_id: UUID,
    payload: Optional[CheckOutRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> AttendanceResponse:
    attendance = attendance_service.check_out_member_active(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        staff_user=current_user,
        payload=payload,
    )
    return attendance_service._to_attendance_response(attendance)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Today's Attendance and History
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/today",
    response_model=AttendanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Today's Attendance List",
    description="Retrieve all check-in entries for today in the gym's configured timezone.",
)
async def get_today_attendance(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> AttendanceListResponse:
    return attendance_service.get_today_attendance(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/members/{member_id}",
    response_model=AttendanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Member Attendance History",
    description="Retrieve historical attendance records for an individual gym member.",
)
async def get_member_attendance_history(
    member_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> AttendanceListResponse:
    return attendance_service.get_member_attendance_history(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/members/{member_id}/qr",
    response_model=MemberQRResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member QR Identifier",
    description="Retrieve or auto-generate secure opaque QR code token for a member.",
)
async def get_member_qr(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MemberQRResponse:
    return attendance_service.get_or_create_member_qr(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
    )


@router.post(
    "/members/{member_id}/qr/regenerate",
    response_model=MemberQRResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate Member QR Identifier",
    description="Revoke previous QR code token and generate a fresh secure token (OWNER / MANAGER only).",
)
async def regenerate_member_qr(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> MemberQRResponse:
    return attendance_service.regenerate_member_qr(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. Analytics Endpoints (OWNER / MANAGER only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/summary",
    response_model=AttendanceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Daily Attendance Totals",
    description="Calculate daily check-ins, unique members, active visits, and completed visits.",
)
async def get_attendance_summary(
    target_date: Optional[date] = Query(None, description="Target business date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> AttendanceSummaryResponse:
    return attendance_service.get_daily_attendance_summary(
        db=db,
        tenant_id=current_user.tenant_id,
        target_date=target_date,
    )


@router.get(
    "/analytics/peak-hours",
    response_model=PeakHoursResponse,
    status_code=status.HTTP_200_OK,
    summary="Peak-Hour Attendance Analysis",
    description="Hourly check-in distribution (00:00 - 23:00) in gym's timezone to detect peak facility hours.",
)
async def get_peak_hours(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> PeakHoursResponse:
    return attendance_service.get_peak_hours_analytics(
        db=db,
        tenant_id=current_user.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/analytics/frequency",
    response_model=AttendanceFrequencyResponse,
    status_code=status.HTTP_200_OK,
    summary="Member Attendance Frequency",
    description="Frequency distribution of member visits and top gym attendees for retention tracking.",
)
async def get_attendance_frequency(
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Top member limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> AttendanceFrequencyResponse:
    return attendance_service.get_member_attendance_frequency(
        db=db,
        tenant_id=current_user.tenant_id,
        from_date=from_date,
        to_date=to_date,
        top_limit=limit,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 5. Gym Attendance Settings Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/settings",
    response_model=AttendanceSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Gym Attendance Settings",
    description="Retrieve gym-level attendance and check-in configuration policies.",
)
async def get_attendance_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> AttendanceSettingsResponse:
    return attendance_service.get_attendance_settings(
        db=db,
        tenant_id=current_user.tenant_id,
    )


@router.patch(
    "/settings",
    response_model=AttendanceSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Gym Attendance Settings",
    description="Update gym check-in policies for expired memberships and dues (OWNER only).",
)
async def update_attendance_settings(
    payload: AttendanceSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ADMIN_ROLES)),
) -> AttendanceSettingsResponse:
    return attendance_service.update_attendance_settings(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 6. General Attendance Query & Action by Attendance ID
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=AttendanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Attendance Records",
    description="Paginated attendance records filtered by date range, method, active status, or member.",
)
async def list_attendance(
    member_id: Optional[UUID] = Query(None, description="Filter by member UUID"),
    check_in_method: Optional[CheckInMethod] = Query(None, description="Filter by method"),
    is_override: Optional[bool] = Query(None, description="Filter overrides"),
    is_active: Optional[bool] = Query(None, description="Filter currently active visits"),
    from_date: Optional[date] = Query(None, description="Check-in on or after YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Check-in on or before YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> AttendanceListResponse:
    return attendance_service.list_attendance(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        check_in_method=check_in_method,
        is_override=is_override,
        is_active=is_active,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{attendance_id}/check-out",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Out Attendance Visit",
    description="Record check-out for a specific attendance record ID.",
)
async def check_out_attendance(
    attendance_id: UUID,
    payload: Optional[CheckOutRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> AttendanceResponse:
    attendance = attendance_service.check_out_attendance(
        db=db,
        tenant_id=current_user.tenant_id,
        attendance_id=attendance_id,
        staff_user=current_user,
        payload=payload,
    )
    return attendance_service._to_attendance_response(attendance)

