"""Report service — business logic and query execution for all GymCore reports."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.member import Member
from app.models.membership import Membership, MembershipStatus
from app.models.membership_plan import MembershipPlan
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.receipt import Receipt
from app.models.refund import Refund, RefundType, RefundStatus
from app.models.attendance import Attendance, CheckInMethod
from app.schemas.reports import (
    RevenuePaymentItem,
    RevenueReportSummary,
    RevenueReportResponse,
    MembershipReportItem,
    MembershipReportSummary,
    MembershipReportResponse,
    AttendanceReportItem,
    AttendanceReportSummary,
    AttendanceReportResponse,
    PendingDueReportItem,
    PendingDuesReportSummary,
    PendingDuesReportResponse,
    ExpiryReportItem,
    ExpiryReportSummary,
    ExpiryReportResponse,
)


def _get_tenant_tz(db: Session, tenant_id: uuid.UUID) -> ZoneInfo:
    """Retrieve gym timezone, defaulting to Asia/Kolkata."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.timezone:
        try:
            return ZoneInfo(tenant.timezone)
        except Exception:
            pass
    return ZoneInfo("Asia/Kolkata")


def _get_range_bounds(tz: ZoneInfo, start_date: date, end_date: date):
    """Convert local start and end dates to UTC boundaries."""
    start_local = datetime.combine(start_date, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(end_date, time.max).replace(tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Revenue & Collection Report
# ──────────────────────────────────────────────────────────────────────────────

def generate_revenue_report(
    db: Session,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    payment_method: Optional[str] = None,
) -> RevenueReportResponse:
    """
    Generate revenue and collection report within a date range.
    Includes gross collection, method-wise distribution, refunds/reversals, and net collections.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    tz = _get_tenant_tz(db, tenant_id)
    start_utc, end_utc = _get_range_bounds(tz, start_date, end_date)

    valid_statuses = (
        PaymentStatus.COMPLETED,
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
        PaymentStatus.REVERSED,
    )

    query = (
        db.query(Payment)
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_(valid_statuses),
            Payment.payment_date >= start_utc,
            Payment.payment_date <= end_utc,
        )
    )

    if payment_method:
        try:
            pm_enum = PaymentMethod[payment_method.upper()]
            query = query.filter(Payment.payment_method == pm_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method: {payment_method}",
            )

    payments = query.order_by(desc(Payment.payment_date)).all()

    # Calculate method breakdown
    method_breakdown: Dict[str, int] = {
        "CASH": 0,
        "UPI": 0,
        "CARD": 0,
        "BANK_TRANSFER": 0,
        "CHEQUE": 0,
    }
    total_gross = 0
    transaction_items: List[RevenuePaymentItem] = []

    for p in payments:
        pm_str = p.payment_method.value if hasattr(p.payment_method, "value") else str(p.payment_method)
        method_breakdown[pm_str] = method_breakdown.get(pm_str, 0) + p.amount_paise
        total_gross += p.amount_paise

        inv = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        mem = db.query(Member).filter(Member.id == inv.member_id).first() if inv else None
        receipt = db.query(Receipt).filter(Receipt.payment_id == p.id).first()

        transaction_items.append(
            RevenuePaymentItem(
                payment_id=p.id,
                invoice_number=inv.invoice_number if inv else None,
                member_name=mem.full_name if mem else "Unknown",
                member_id=mem.id if mem else uuid.UUID(int=0),
                amount_paise=p.amount_paise,
                amount_rupees=round(p.amount_paise / 100.0, 2),
                payment_method=pm_str,
                payment_status=p.payment_status.value if hasattr(p.payment_status, "value") else str(p.payment_status),
                payment_date=p.payment_date,
                receipt_number=receipt.receipt_number if receipt else None,
            )
        )

    # Refunds & reversals within the period
    refunds = (
        db.query(Refund)
        .filter(
            Refund.tenant_id == tenant_id,
            Refund.status == RefundStatus.COMPLETED,
            Refund.created_at >= start_utc,
            Refund.created_at <= end_utc,
        )
        .all()
    )
    total_refunds = sum(r.amount_paise for r in refunds if r.refund_type == RefundType.REFUND)
    total_reversals = sum(r.amount_paise for r in refunds if r.refund_type == RefundType.REVERSAL)
    total_net = max(0, total_gross - total_refunds - total_reversals)

    summary = RevenueReportSummary(
        total_gross_paise=total_gross,
        total_gross_rupees=round(total_gross / 100.0, 2),
        total_refunds_paise=total_refunds,
        total_refunds_rupees=round(total_refunds / 100.0, 2),
        total_reversals_paise=total_reversals,
        total_reversals_rupees=round(total_reversals / 100.0, 2),
        total_net_paise=total_net,
        total_net_rupees=round(total_net / 100.0, 2),
        transaction_count=len(payments),
        by_payment_method=method_breakdown,
    )

    return RevenueReportResponse(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        transactions=transaction_items,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Membership Report
# ──────────────────────────────────────────────────────────────────────────────

def generate_membership_report(
    db: Session,
    tenant_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    plan_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
) -> MembershipReportResponse:
    """Generate membership report with status distributions and plan breakdowns."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    query = db.query(Membership).filter(Membership.tenant_id == tenant_id)

    if start_date:
        query = query.filter(Membership.start_date >= start_date)
    if end_date:
        query = query.filter(Membership.start_date <= end_date)
    if plan_id:
        query = query.filter(Membership.membership_plan_id == plan_id)
    if status_filter:
        try:
            st_enum = MembershipStatus[status_filter.upper()]
            query = query.filter(Membership.status == st_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid membership status: {status_filter}",
            )

    memberships = query.order_by(desc(Membership.created_at)).all()

    by_plan: Dict[str, int] = {}
    active_count = 0
    expired_count = 0
    frozen_count = 0
    cancelled_count = 0
    items: List[MembershipReportItem] = []

    for m in memberships:
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.membership_plan_id).first()
        mem = db.query(Member).filter(Member.id == m.member_id).first()

        plan_name = plan.name if plan else "Unknown Plan"
        price_rupees = float(plan.price) if plan and plan.price is not None else 0.0
        price_paise = int(round(price_rupees * 100))
        by_plan[plan_name] = by_plan.get(plan_name, 0) + 1

        if m.status == MembershipStatus.ACTIVE:
            active_count += 1
        elif m.status == MembershipStatus.EXPIRED:
            expired_count += 1
        elif m.status == MembershipStatus.FROZEN:
            frozen_count += 1
        elif m.status == MembershipStatus.CANCELLED:
            cancelled_count += 1

        items.append(
            MembershipReportItem(
                membership_id=m.id,
                member_id=m.member_id,
                member_name=mem.full_name if mem else "Unknown",
                member_phone=mem.phone if mem else None,
                plan_name=plan_name,
                start_date=m.start_date,
                end_date=m.end_date,
                status=m.status.value if hasattr(m.status, "value") else str(m.status),
                price_paise=price_paise,
                price_rupees=round(price_paise / 100.0, 2),
            )
        )

    summary = MembershipReportSummary(
        total_memberships=len(memberships),
        active_count=active_count,
        expired_count=expired_count,
        frozen_count=frozen_count,
        cancelled_count=cancelled_count,
        by_plan=by_plan,
    )

    return MembershipReportResponse(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        memberships=items,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 3. Attendance Report
# ──────────────────────────────────────────────────────────────────────────────

def generate_attendance_report(
    db: Session,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    member_id: Optional[uuid.UUID] = None,
    check_in_method: Optional[str] = None,
) -> AttendanceReportResponse:
    """Generate attendance report with visits, peak hours, and check-in methods."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    tz = _get_tenant_tz(db, tenant_id)
    start_utc, end_utc = _get_range_bounds(tz, start_date, end_date)

    query = (
        db.query(Attendance)
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.check_in_time >= start_utc,
            Attendance.check_in_time <= end_utc,
        )
    )

    if member_id:
        query = query.filter(Attendance.member_id == member_id)
    if check_in_method:
        try:
            m_enum = CheckInMethod[check_in_method.upper()]
            query = query.filter(Attendance.check_in_method == m_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid check-in method: {check_in_method}",
            )

    visits = query.order_by(desc(Attendance.check_in_time)).all()

    by_method: Dict[str, int] = {"MANUAL": 0, "QR": 0}
    by_time_slot: Dict[str, int] = {
        "Morning (05:00-12:00)": 0,
        "Afternoon (12:00-17:00)": 0,
        "Evening (17:00-22:00)": 0,
        "Night (22:00-05:00)": 0,
    }
    unique_members_set = set()
    overridden_count = 0
    items: List[AttendanceReportItem] = []

    for v in visits:
        unique_members_set.add(v.member_id)
        if v.override_reason:
            overridden_count += 1

        method_str = v.check_in_method.value if hasattr(v.check_in_method, "value") else str(v.check_in_method)
        by_method[method_str] = by_method.get(method_str, 0) + 1

        # Calculate time slot in tenant's timezone
        local_check_in = v.check_in_time.astimezone(tz)
        hour = local_check_in.hour
        if 5 <= hour < 12:
            by_time_slot["Morning (05:00-12:00)"] += 1
        elif 12 <= hour < 17:
            by_time_slot["Afternoon (12:00-17:00)"] += 1
        elif 17 <= hour < 22:
            by_time_slot["Evening (17:00-22:00)"] += 1
        else:
            by_time_slot["Night (22:00-05:00)"] += 1

        mem = db.query(Member).filter(Member.id == v.member_id).first()
        items.append(
            AttendanceReportItem(
                attendance_id=v.id,
                member_id=v.member_id,
                member_name=mem.full_name if mem else "Unknown",
                member_phone=mem.phone if mem else None,
                check_in_time=v.check_in_time,
                check_out_time=v.check_out_time,
                check_in_method=method_str,
                override_reason=v.override_reason,
            )
        )

    num_days = max(1, (end_date - start_date).days + 1)
    avg_daily = round(len(visits) / float(num_days), 2)

    summary = AttendanceReportSummary(
        total_visits=len(visits),
        unique_members=len(unique_members_set),
        avg_daily_visits=avg_daily,
        overridden_visits_count=overridden_count,
        by_method=by_method,
        by_time_slot=by_time_slot,
    )

    return AttendanceReportResponse(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        visits=items,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pending Dues & Billing Report
# ──────────────────────────────────────────────────────────────────────────────

def generate_pending_dues_report(
    db: Session,
    tenant_id: uuid.UUID,
    ageing_bucket: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> PendingDuesReportResponse:
    """Generate pending dues report with ageing breakdown and member balances."""
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()

    pending_statuses = [
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    ]

    query = (
        db.query(Invoice)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_status.in_(pending_statuses),
            Invoice.balance_amount_paise > 0,
        )
    )

    if status_filter:
        try:
            st_enum = InvoiceStatus[status_filter.upper()]
            query = query.filter(Invoice.invoice_status == st_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid invoice status: {status_filter}",
            )

    invoices = query.order_by(desc(Invoice.balance_amount_paise)).all()

    total_outstanding = 0
    bucket_0_7 = 0
    bucket_8_30 = 0
    bucket_30_plus = 0
    bucket_current = 0
    all_items: List[PendingDueReportItem] = []

    for inv in invoices:
        days_overdue = (today - inv.due_date).days
        if days_overdue <= 0:
            bucket = "current"
            bucket_current += inv.balance_amount_paise
        elif 1 <= days_overdue <= 7:
            bucket = "0-7 days"
            bucket_0_7 += inv.balance_amount_paise
        elif 8 <= days_overdue <= 30:
            bucket = "8-30 days"
            bucket_8_30 += inv.balance_amount_paise
        else:
            bucket = "30+ days"
            bucket_30_plus += inv.balance_amount_paise

        total_outstanding += inv.balance_amount_paise

        # Filter by bucket if requested
        if ageing_bucket:
            clean_bucket = ageing_bucket.strip().lower()
            if clean_bucket in ("0-7", "0-7 days") and bucket != "0-7 days":
                continue
            elif clean_bucket in ("8-30", "8-30 days") and bucket != "8-30 days":
                continue
            elif clean_bucket in ("30+", "30+ days", ">30") and bucket != "30+ days":
                continue
            elif clean_bucket == "current" and bucket != "current":
                continue

        mem = db.query(Member).filter(Member.id == inv.member_id).first()
        all_items.append(
            PendingDueReportItem(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                member_id=inv.member_id,
                member_name=mem.full_name if mem else "Unknown",
                member_phone=mem.phone if mem else None,
                issue_date=inv.issue_date,
                due_date=inv.due_date,
                total_amount_paise=inv.amount_paise,
                paid_amount_paise=inv.paid_amount_paise,
                balance_amount_paise=inv.balance_amount_paise,
                balance_amount_rupees=round(inv.balance_amount_paise / 100.0, 2),
                days_overdue=max(0, days_overdue),
                status=inv.invoice_status.value if hasattr(inv.invoice_status, "value") else str(inv.invoice_status),
                ageing_bucket=bucket,
            )
        )

    summary = PendingDuesReportSummary(
        total_outstanding_paise=total_outstanding,
        total_outstanding_rupees=round(total_outstanding / 100.0, 2),
        total_pending_invoices=len(invoices),
        bucket_0_7_paise=bucket_0_7,
        bucket_8_30_paise=bucket_8_30,
        bucket_30_plus_paise=bucket_30_plus,
        bucket_current_paise=bucket_current,
    )

    return PendingDuesReportResponse(
        tenant_id=tenant_id,
        summary=summary,
        invoices=all_items,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 5. Membership Expiry & Renewal Report
# ──────────────────────────────────────────────────────────────────────────────

def generate_expiry_report(
    db: Session,
    tenant_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[str] = None,
) -> ExpiryReportResponse:
    """Generate membership expiry report categorized into EXPIRING_SOON, EXPIRING_TODAY, EXPIRED, LAPSED."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()

    grace_days = tenant.membership_lapsed_grace_days if tenant and tenant.membership_lapsed_grace_days else 30

    query = db.query(Membership).filter(Membership.tenant_id == tenant_id)

    if start_date:
        query = query.filter(Membership.end_date >= start_date)
    if end_date:
        query = query.filter(Membership.end_date <= end_date)

    memberships = query.order_by(Membership.end_date.asc()).all()

    soon_count = 0
    today_count = 0
    expired_count = 0
    lapsed_count = 0
    items: List[ExpiryReportItem] = []

    for m in memberships:
        days_rem = (m.end_date - today).days

        if days_rem > 0:
            cat = "EXPIRING_SOON"
            soon_count += 1
        elif days_rem == 0:
            cat = "EXPIRING_TODAY"
            today_count += 1
        elif abs(days_rem) <= grace_days:
            cat = "EXPIRED"
            expired_count += 1
        else:
            cat = "LAPSED"
            lapsed_count += 1

        if status_filter:
            if status_filter.upper() != "ALL" and cat != status_filter.upper():
                continue

        mem = db.query(Member).filter(Member.id == m.member_id).first()
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.membership_plan_id).first()

        items.append(
            ExpiryReportItem(
                membership_id=m.id,
                member_id=m.member_id,
                member_name=mem.full_name if mem else "Unknown",
                member_phone=mem.phone if mem else None,
                plan_name=plan.name if plan else "Unknown Plan",
                end_date=m.end_date,
                days_remaining=days_rem,
                status=cat,
            )
        )

    summary = ExpiryReportSummary(
        total_count=len(memberships),
        expiring_soon_count=soon_count,
        expiring_today_count=today_count,
        expired_count=expired_count,
        lapsed_count=lapsed_count,
    )

    return ExpiryReportResponse(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        items=items,
    )

