"""Attendance service — member check-in/check-out, QR validation, eligibility engine, and analytics."""
import math
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_, distinct, case
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.models.membership import Membership, MembershipStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.attendance import Attendance, CheckInMethod
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
from app.services.invoice_service import get_gym_today
from app.services.audit_service import log_audit_event


def _get_tenant_tz(db: Session, tenant_id: uuid.UUID) -> str:
    """Retrieve gym timezone, defaulting to Asia/Kolkata."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.timezone:
        return tenant.timezone
    return "Asia/Kolkata"


def _generate_secure_qr_code() -> str:
    """Generate an opaque, unguessable, secure random QR token."""
    return f"GYM_{uuid.uuid4().hex[:8]}_{secrets.token_urlsafe(18)}"


# ──────────────────────────────────────────────────────────────────────────────
# Member Search for Check-in Desk
# ──────────────────────────────────────────────────────────────────────────────

def search_members_for_checkin(
    db: Session,
    tenant_id: uuid.UUID,
    query_str: str,
    limit: int = 20,
) -> List[MemberSearchResult]:
    """
    Search gym members by name, phone number, or member code.
    Populates current membership status and active check-in indicator.
    """
    q = query_str.strip()
    if not q:
        return []

    pattern = f"%{q}%"
    members = (
        db.query(Member)
        .filter(
            Member.tenant_id == tenant_id,
            or_(
                Member.full_name.ilike(pattern),
                Member.phone.ilike(pattern),
                Member.member_code.ilike(pattern),
            ),
        )
        .limit(limit)
        .all()
    )

    results: List[MemberSearchResult] = []
    for m in members:
        # Check if member has active check-in
        active_att = (
            db.query(Attendance)
            .filter(
                Attendance.tenant_id == tenant_id,
                Attendance.member_id == m.id,
                Attendance.check_out_time.is_(None),
            )
            .first()
        )

        # Get latest membership
        latest_ms = (
            db.query(Membership)
            .filter(Membership.tenant_id == tenant_id, Membership.member_id == m.id)
            .order_by(Membership.created_at.desc())
            .first()
        )

        plan_name = latest_ms.membership_plan.name if (latest_ms and latest_ms.membership_plan) else None
        ms_status = latest_ms.status.value if latest_ms else None
        end_date = latest_ms.end_date if latest_ms else None

        results.append(
            MemberSearchResult(
                member_id=m.id,
                full_name=m.full_name,
                phone=m.phone,
                email=m.email,
                member_code=m.member_code,
                qr_code=m.qr_code,
                member_status=m.status,
                active_membership_status=ms_status,
                plan_name=plan_name,
                membership_end_date=end_date,
                is_currently_checked_in=active_att is not None,
                active_attendance_id=active_att.id if active_att else None,
            )
        )

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Membership Eligibility Engine
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_membership_eligibility(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
) -> EligibilityResponse:
    """
    Centralized and reusable membership eligibility validation.
    Evaluates dates, lifecycle status, freeze periods, dues, and gym policies.
    """
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this tenant",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    block_expired = tenant.attendance_block_expired if tenant else True
    block_dues = tenant.attendance_block_on_dues if tenant else False

    # 1. Outstanding dues check
    unpaid_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.member_id == member_id,
            Invoice.invoice_status != InvoiceStatus.CANCELLED,
            Invoice.balance_amount_paise > 0,
        )
        .all()
    )
    total_dues_paise = sum(i.balance_amount_paise for i in unpaid_invoices)
    has_dues = total_dues_paise > 0

    # 2. Retrieve latest membership
    membership = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant_id, Membership.member_id == member_id)
        .order_by(Membership.created_at.desc())
        .first()
    )

    if not membership:
        return EligibilityResponse(
            eligible=False,
            member_id=member.id,
            member_name=member.full_name,
            membership_id=None,
            membership_status="NONE",
            plan_name=None,
            start_date=None,
            end_date=None,
            warning="Member has no registered membership subscription",
            override_permitted=True,
            has_outstanding_dues=has_dues,
            outstanding_dues_paise=total_dues_paise,
        )

    today = get_gym_today(db, tenant_id)
    plan_name = membership.membership_plan.name if membership.membership_plan else None

    # Date-based evaluation
    eligible = False
    warning: Optional[str] = None
    override_permitted = False
    ms_status = membership.status.value

    if membership.status == MembershipStatus.ACTIVE:
        if membership.start_date > today:
            ms_status = "FUTURE"
            eligible = False
            warning = f"Membership starts in the future on {membership.start_date.isoformat()}"
            override_permitted = True
        elif membership.end_date < today:
            ms_status = "EXPIRED"
            if block_expired:
                eligible = False
                warning = f"Membership expired on {membership.end_date.isoformat()}"
                override_permitted = True
            else:
                eligible = True
                warning = f"Membership expired on {membership.end_date.isoformat()} (allowed by gym policy)"
                override_permitted = False
        elif membership.end_date <= today + timedelta(days=5):
            ms_status = "EXPIRING"
            eligible = True
            warning = f"Membership is expiring soon on {membership.end_date.isoformat()}"
            override_permitted = False
        else:
            eligible = True
            warning = None
            override_permitted = False

    elif membership.status == MembershipStatus.FROZEN:
        ms_status = "FROZEN"
        eligible = False
        freeze_until = f" until {membership.freeze_end_date.isoformat()}" if membership.freeze_end_date else ""
        warning = f"Membership is currently frozen{freeze_until}"
        override_permitted = True

    elif membership.status == MembershipStatus.CANCELLED:
        ms_status = "CANCELLED"
        eligible = False
        warning = "Membership subscription was cancelled"
        override_permitted = True

    elif membership.status == MembershipStatus.EXPIRED:
        ms_status = "EXPIRED"
        if block_expired:
            eligible = False
            warning = f"Membership expired on {membership.end_date.isoformat()}"
            override_permitted = True
        else:
            eligible = True
            warning = f"Membership expired on {membership.end_date.isoformat()} (allowed by gym policy)"
            override_permitted = False

    else:
        eligible = False
        warning = f"Membership is currently {ms_status}"
        override_permitted = True

    # 3. Apply dues policy
    if has_dues:
        dues_str = f"₹{total_dues_paise / 100:.2f}"
        if block_dues:
            eligible = False
            warning = f"Check-in blocked: Member has overdue payments of {dues_str}"
            override_permitted = True
        else:
            dues_warning = f"Note: Member has overdue balance of {dues_str}"
            warning = f"{warning}; {dues_warning}" if warning else dues_warning

    return EligibilityResponse(
        eligible=eligible,
        member_id=member.id,
        member_name=member.full_name,
        membership_id=membership.id,
        membership_status=ms_status,
        plan_name=plan_name,
        start_date=membership.start_date,
        end_date=membership.end_date,
        warning=warning,
        override_permitted=override_permitted,
        has_outstanding_dues=has_dues,
        outstanding_dues_paise=total_dues_paise,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Check-in and Check-out Workflows
# ──────────────────────────────────────────────────────────────────────────────

def check_in_member(
    db: Session,
    tenant_id: uuid.UUID,
    payload: CheckInRequest,
    staff_user: User,
) -> Attendance:
    """Perform manual check-in with membership validation and optional authorized override."""
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # 1. Prevent duplicate active check-in
    active = (
        db.query(Attendance)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.member_id == payload.member_id,
            Attendance.check_out_time.is_(None),
        )
        .with_for_update()
        .first()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Member is already checked in (Visit ID: {active.id}). Check out previous visit first.",
        )

    # 2. Check membership eligibility
    eligibility = evaluate_membership_eligibility(db, tenant_id, payload.member_id)

    is_override = False
    override_reason: Optional[str] = None
    override_by_id: Optional[uuid.UUID] = None

    if not eligibility.eligible:
        if payload.override:
            # Enforce override RBAC
            if staff_user.role not in (UserRole.OWNER, UserRole.MANAGER):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operation not permitted. Only OWNER or MANAGER can override check-in restrictions.",
                )
            if not payload.override_reason or not payload.override_reason.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mandatory override reason is required to bypass membership restriction.",
                )
            is_override = True
            override_reason = payload.override_reason.strip()
            override_by_id = staff_user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Check-in blocked: {eligibility.warning}. Authorized override with reason required.",
            )

    attendance = Attendance(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=payload.member_id,
        check_in_time=datetime.now(timezone.utc),
        check_out_time=None,
        check_in_method=CheckInMethod.MANUAL,
        checked_in_by_id=staff_user.id,
        is_override=is_override,
        override_reason=override_reason,
        override_by_id=override_by_id,
    )

    db.add(attendance)

    if is_override:
        log_audit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=staff_user.id,
            action="ATTENDANCE_OVERRIDE",
            resource_type="ATTENDANCE",
            resource_id=str(attendance.id),
            after_values={"member_id": str(payload.member_id), "is_override": True},
            reason=override_reason,
        )

    db.commit()
    db.refresh(attendance)
    return attendance


def qr_check_in(
    db: Session,
    tenant_id: uuid.UUID,
    payload: QRCheckInRequest,
    staff_user: Optional[User] = None,
) -> Attendance:
    """Validate member's secure QR code and record QR-based attendance."""
    member = (
        db.query(Member)
        .filter(Member.qr_code == payload.qr_code, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or unrecognized QR code for this gym",
        )

    # 1. Prevent duplicate active check-in
    active = (
        db.query(Attendance)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.member_id == member.id,
            Attendance.check_out_time.is_(None),
        )
        .with_for_update()
        .first()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Member is already checked in (Visit ID: {active.id}). Check out previous visit first.",
        )

    # 2. Eligibility
    eligibility = evaluate_membership_eligibility(db, tenant_id, member.id)

    is_override = False
    override_reason: Optional[str] = None
    override_by_id: Optional[uuid.UUID] = None

    if not eligibility.eligible:
        if payload.override:
            if not staff_user or staff_user.role not in (UserRole.OWNER, UserRole.MANAGER):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operation not permitted. Only OWNER or MANAGER can override check-in restrictions.",
                )
            if not payload.override_reason or not payload.override_reason.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mandatory override reason is required to bypass membership restriction.",
                )
            is_override = True
            override_reason = payload.override_reason.strip()
            override_by_id = staff_user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"QR check-in blocked: {eligibility.warning}.",
            )

    attendance = Attendance(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=member.id,
        check_in_time=datetime.now(timezone.utc),
        check_out_time=None,
        check_in_method=CheckInMethod.QR,
        checked_in_by_id=staff_user.id if staff_user else None,
        is_override=is_override,
        override_reason=override_reason,
        override_by_id=override_by_id,
    )

    db.add(attendance)

    if is_override:
        log_audit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=staff_user.id if staff_user else None,
            action="ATTENDANCE_OVERRIDE",
            resource_type="ATTENDANCE",
            resource_id=str(attendance.id),
            after_values={"member_id": str(member.id), "is_override": True},
            reason=override_reason,
        )

    db.commit()
    db.refresh(attendance)
    return attendance


def check_out_attendance(
    db: Session,
    tenant_id: uuid.UUID,
    attendance_id: uuid.UUID,
    staff_user: User,
    payload: Optional[CheckOutRequest] = None,
) -> Attendance:
    """Record member check-out on an active attendance visit."""
    attendance = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id, Attendance.tenant_id == tenant_id)
        .first()
    )
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    if attendance.check_out_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This visit was already checked out at {attendance.check_out_time.isoformat()}",
        )

    now_utc = datetime.now(timezone.utc)
    attendance.check_out_time = now_utc
    attendance.checked_out_by_id = staff_user.id

    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def check_out_member_active(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    staff_user: User,
    payload: Optional[CheckOutRequest] = None,
) -> Attendance:
    """Locate member's currently active check-in and check out."""
    active = (
        db.query(Attendance)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.member_id == member_id,
            Attendance.check_out_time.is_(None),
        )
        .first()
    )
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active check-in found for this member",
        )

    return check_out_attendance(db, tenant_id, active.id, staff_user, payload)


# ──────────────────────────────────────────────────────────────────────────────
# Attendance History & Querying
# ──────────────────────────────────────────────────────────────────────────────

def _to_attendance_response(att: Attendance) -> AttendanceResponse:
    """Format Attendance model to response schema with populated member and staff names."""
    m_name = att.member.full_name if att.member else None
    m_phone = att.member.phone if att.member else None
    m_code = att.member.member_code if att.member else None
    staff_name = att.checked_in_by.name if att.checked_in_by else None

    return AttendanceResponse(
        id=att.id,
        tenant_id=att.tenant_id,
        member_id=att.member_id,
        member_name=m_name,
        member_phone=m_phone,
        member_code=m_code,
        check_in_time=att.check_in_time,
        check_out_time=att.check_out_time,
        check_in_method=att.check_in_method,
        checked_in_by_id=att.checked_in_by_id,
        checked_in_by_name=staff_name,
        checked_out_by_id=att.checked_out_by_id,
        is_override=att.is_override,
        override_reason=att.override_reason,
        override_by_id=att.override_by_id,
        is_active=att.is_active,
        duration_minutes=att.duration_minutes,
        created_at=att.created_at,
    )


def list_attendance(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: Optional[uuid.UUID] = None,
    check_in_method: Optional[CheckInMethod] = None,
    is_override: Optional[bool] = None,
    is_active: Optional[bool] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> AttendanceListResponse:
    """Retrieve paginated attendance records with optional filters."""
    query = db.query(Attendance).filter(Attendance.tenant_id == tenant_id)

    if member_id is not None:
        query = query.filter(Attendance.member_id == member_id)
    if check_in_method is not None:
        query = query.filter(Attendance.check_in_method == check_in_method)
    if is_override is not None:
        query = query.filter(Attendance.is_override == is_override)
    if is_active is not None:
        if is_active:
            query = query.filter(Attendance.check_out_time.is_(None))
        else:
            query = query.filter(Attendance.check_out_time.isnot(None))

    tz_str = _get_tenant_tz(db, tenant_id)
    tz = ZoneInfo(tz_str)

    if from_date is not None:
        dt_start = datetime.combine(from_date, time.min).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Attendance.check_in_time >= dt_start)
    if to_date is not None:
        dt_end = datetime.combine(to_date, time.max).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Attendance.check_in_time <= dt_end)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size

    records = (
        query.order_by(Attendance.check_in_time.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [_to_attendance_response(r) for r in records]
    return AttendanceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


def get_today_attendance(
    db: Session,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> AttendanceListResponse:
    """List all attendance records for today in the gym's configured timezone."""
    today = get_gym_today(db, tenant_id)
    return list_attendance(
        db=db,
        tenant_id=tenant_id,
        from_date=today,
        to_date=today,
        page=page,
        page_size=page_size,
    )


def get_member_attendance_history(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> AttendanceListResponse:
    """Retrieve visit history for an individual member."""
    # Verify member belongs to tenant
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    return list_attendance(
        db=db,
        tenant_id=tenant_id,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Analytics & Peak-Hour Reporting
# ──────────────────────────────────────────────────────────────────────────────

def get_daily_attendance_summary(
    db: Session,
    tenant_id: uuid.UUID,
    target_date: Optional[date] = None,
) -> AttendanceSummaryResponse:
    """Calculate daily attendance metrics for a specific business date."""
    tz_str = _get_tenant_tz(db, tenant_id)
    tz = ZoneInfo(tz_str)

    if target_date is None:
        target_date = get_gym_today(db, tenant_id)

    start_local = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    # Check-ins on target date
    day_query = db.query(Attendance).filter(
        Attendance.tenant_id == tenant_id,
        Attendance.check_in_time >= start_utc,
        Attendance.check_in_time <= end_utc,
    )

    total_check_ins = day_query.count()
    unique_members = day_query.with_entities(func.count(distinct(Attendance.member_id))).scalar() or 0
    active_check_ins = day_query.filter(Attendance.check_out_time.is_(None)).count()
    completed_visits = total_check_ins - active_check_ins

    return AttendanceSummaryResponse(
        tenant_id=tenant_id,
        date=target_date,
        total_check_ins=total_check_ins,
        unique_members=unique_members,
        active_check_ins=active_check_ins,
        completed_visits=completed_visits,
    )


def get_peak_hours_analytics(
    db: Session,
    tenant_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> PeakHoursResponse:
    """
    Aggregate check-ins into hourly intervals (00:00 to 23:00) in gym's timezone
    to identify capacity utilization and peak visit periods.
    """
    tz_str = _get_tenant_tz(db, tenant_id)
    tz = ZoneInfo(tz_str)
    today = get_gym_today(db, tenant_id)

    if to_date is None:
        to_date = today
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    start_utc = datetime.combine(from_date, time.min).replace(tzinfo=tz).astimezone(timezone.utc)
    end_utc = datetime.combine(to_date, time.max).replace(tzinfo=tz).astimezone(timezone.utc)

    records = (
        db.query(Attendance.check_in_time)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.check_in_time >= start_utc,
            Attendance.check_in_time <= end_utc,
        )
        .all()
    )

    hourly_counts = {h: 0 for h in range(24)}
    for r in records:
        # Convert check-in UTC time to tenant's timezone
        local_time = r[0].astimezone(tz)
        hourly_counts[local_time.hour] += 1

    breakdown = []
    peak_h: Optional[int] = None
    peak_count = 0

    for h in range(24):
        cnt = hourly_counts[h]
        lbl = f"{h:02d}:00 - {(h + 1) % 24:02d}:00"
        breakdown.append({"hour": h, "hour_label": lbl, "count": cnt})
        if cnt > peak_count:
            peak_count = cnt
            peak_h = h

    peak_lbl = f"{peak_h:02d}:00 - {(peak_h + 1) % 24:02d}:00" if peak_h is not None else None

    return PeakHoursResponse(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        hourly_breakdown=breakdown,
        peak_hour=peak_h,
        peak_hour_label=peak_lbl,
        peak_hour_count=peak_count,
    )


def get_member_attendance_frequency(
    db: Session,
    tenant_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    top_limit: int = 10,
) -> AttendanceFrequencyResponse:
    """Calculate visit frequencies across members for retention and engagement analysis."""
    tz_str = _get_tenant_tz(db, tenant_id)
    tz = ZoneInfo(tz_str)
    today = get_gym_today(db, tenant_id)

    if to_date is None:
        to_date = today
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    start_utc = datetime.combine(from_date, time.min).replace(tzinfo=tz).astimezone(timezone.utc)
    end_utc = datetime.combine(to_date, time.max).replace(tzinfo=tz).astimezone(timezone.utc)

    # Group visits by member
    member_counts = (
        db.query(
            Attendance.member_id,
            Member.full_name,
            func.count(Attendance.id).label("visit_count"),
        )
        .join(Member, Member.id == Attendance.member_id)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.check_in_time >= start_utc,
            Attendance.check_in_time <= end_utc,
        )
        .group_by(Attendance.member_id, Member.full_name)
        .order_by(func.count(Attendance.id).desc())
        .all()
    )

    total_visits = sum(row.visit_count for row in member_counts)
    unique_members = len(member_counts)

    top_members = [
        {"member_id": str(r.member_id), "member_name": r.full_name, "visit_count": r.visit_count}
        for r in member_counts[:top_limit]
    ]

    # Frequency buckets
    distribution = {
        "1-4 visits": 0,
        "5-9 visits": 0,
        "10-19 visits": 0,
        "20+ visits": 0,
    }
    for r in member_counts:
        v = r.visit_count
        if v < 5:
            distribution["1-4 visits"] += 1
        elif v < 10:
            distribution["5-9 visits"] += 1
        elif v < 20:
            distribution["10-19 visits"] += 1
        else:
            distribution["20+ visits"] += 1

    return AttendanceFrequencyResponse(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        total_visits=total_visits,
        unique_members=unique_members,
        top_members=top_members,
        frequency_distribution=distribution,
    )


# ──────────────────────────────────────────────────────────────────────────────
# QR Code & Gym Settings Management
# ──────────────────────────────────────────────────────────────────────────────

def get_or_create_member_qr(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
) -> MemberQRResponse:
    """Retrieve or generate secure QR identifier for a member."""
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if not member.qr_code:
        member.qr_code = _generate_secure_qr_code()
        db.add(member)
        db.commit()
        db.refresh(member)

    return MemberQRResponse(
        member_id=member.id,
        member_name=member.full_name,
        member_code=member.member_code,
        qr_code=member.qr_code,
    )


def regenerate_member_qr(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
) -> MemberQRResponse:
    """Revoke existing QR token and generate a fresh secure token."""
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.qr_code = _generate_secure_qr_code()
    db.add(member)
    db.commit()
    db.refresh(member)

    return MemberQRResponse(
        member_id=member.id,
        member_name=member.full_name,
        member_code=member.member_code,
        qr_code=member.qr_code,
    )


def get_attendance_settings(db: Session, tenant_id: uuid.UUID) -> AttendanceSettingsResponse:
    """Retrieve gym's attendance and check-in configuration."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return AttendanceSettingsResponse(
        tenant_id=tenant.id,
        attendance_block_expired=tenant.attendance_block_expired,
        attendance_allow_override=tenant.attendance_allow_override,
        attendance_block_on_dues=tenant.attendance_block_on_dues,
    )


def update_attendance_settings(
    db: Session,
    tenant_id: uuid.UUID,
    payload: AttendanceSettingsUpdateRequest,
) -> AttendanceSettingsResponse:
    """Update gym check-in policies (OWNER / MANAGER only)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if payload.attendance_block_expired is not None:
        tenant.attendance_block_expired = payload.attendance_block_expired
    if payload.attendance_allow_override is not None:
        tenant.attendance_allow_override = payload.attendance_allow_override
    if payload.attendance_block_on_dues is not None:
        tenant.attendance_block_on_dues = payload.attendance_block_on_dues

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return AttendanceSettingsResponse(
        tenant_id=tenant.id,
        attendance_block_expired=tenant.attendance_block_expired,
        attendance_allow_override=tenant.attendance_allow_override,
        attendance_block_on_dues=tenant.attendance_block_on_dues,
    )

