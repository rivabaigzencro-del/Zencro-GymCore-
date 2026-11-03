"""Dashboard service — aggregated statistics, financial KPIs, and activity feeds."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.member import Member, MemberStatus
from app.models.membership import Membership, MembershipStatus
from app.models.membership_plan import MembershipPlan
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.refund import Refund, RefundStatus
from app.models.receipt import Receipt
from app.models.attendance import Attendance
from app.schemas.dashboard import (
    MemberStats,
    FinancialStats,
    MembershipStats,
    AttendanceDailyTrend,
    AttendanceStats,
    RecentPaymentItem,
    UpcomingRenewalItem,
    PendingDueItem,
    RecentRegistrationItem,
    RecentAttendanceItem,
    DashboardSummaryResponse,
)


def _get_tenant_tz(db: Session, tenant_id: uuid.UUID) -> ZoneInfo:
    """Retrieve tenant timezone, defaulting to Asia/Kolkata."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.timezone:
        try:
            return ZoneInfo(tenant.timezone)
        except Exception:
            pass
    return ZoneInfo("Asia/Kolkata")


def _get_time_bounds(tz: ZoneInfo, target_date: date):
    """Calculate UTC start and end bounds for a given date in tenant's timezone."""
    start_local = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _get_month_bounds(tz: ZoneInfo, target_date: date):
    """Calculate UTC start of month and end of month bounds in tenant's timezone."""
    first_day = target_date.replace(day=1)
    # Next month first day minus 1 day
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    last_day = next_month - timedelta(days=1)

    start_local = datetime.combine(first_day, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(last_day, time.max).replace(tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# KPI Calculation Functions
# ──────────────────────────────────────────────────────────────────────────────

def get_member_stats(db: Session, tenant_id: uuid.UUID) -> MemberStats:
    """Calculate member count statistics strictly for the tenant."""
    total_members = (
        db.query(func.count(Member.id))
        .filter(Member.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    active_members = (
        db.query(func.count(Member.id))
        .filter(Member.tenant_id == tenant_id, Member.status == MemberStatus.ACTIVE)
        .scalar()
        or 0
    )
    inactive_members = (
        db.query(func.count(Member.id))
        .filter(Member.tenant_id == tenant_id, Member.status == MemberStatus.INACTIVE)
        .scalar()
        or 0
    )
    expired_count = (
        db.query(func.count(func.distinct(Membership.member_id)))
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.EXPIRED,
        )
        .scalar()
        or 0
    )
    return MemberStats(
        total_members=total_members,
        active_members=active_members,
        inactive_members=inactive_members,
        expired_memberships=expired_count,
    )


def get_financial_stats(db: Session, tenant_id: uuid.UUID) -> FinancialStats:
    """
    Calculate financial metrics: all-time net revenue, today's net collection,
    monthly net collection, and pending dues in integer paise and decimal rupees.
    Excludes pending or failed payments from collected revenue.
    """
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()
    today_start_utc, today_end_utc = _get_time_bounds(tz, today)
    month_start_utc, month_end_utc = _get_month_bounds(tz, today)

    # Valid statuses for collected payments
    valid_payment_statuses = (
        PaymentStatus.COMPLETED,
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
        PaymentStatus.REVERSED,
    )

    # All-time Gross & Net
    all_time_gross = (
        db.query(func.sum(Payment.amount_paise))
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_(valid_payment_statuses),
        )
        .scalar()
        or 0
    )
    all_time_refunds = (
        db.query(func.sum(Refund.amount_paise))
        .filter(
            Refund.tenant_id == tenant_id,
            Refund.status == RefundStatus.COMPLETED,
        )
        .scalar()
        or 0
    )
    total_net_paise = max(0, all_time_gross - all_time_refunds)

    # Today's Collection
    today_gross = (
        db.query(func.sum(Payment.amount_paise))
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_(valid_payment_statuses),
            Payment.payment_date >= today_start_utc,
            Payment.payment_date <= today_end_utc,
        )
        .scalar()
        or 0
    )
    today_refunds = (
        db.query(func.sum(Refund.amount_paise))
        .filter(
            Refund.tenant_id == tenant_id,
            Refund.status == RefundStatus.COMPLETED,
            Refund.created_at >= today_start_utc,
            Refund.created_at <= today_end_utc,
        )
        .scalar()
        or 0
    )
    today_net_paise = max(0, today_gross - today_refunds)

    # Monthly Collection
    month_gross = (
        db.query(func.sum(Payment.amount_paise))
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_(valid_payment_statuses),
            Payment.payment_date >= month_start_utc,
            Payment.payment_date <= month_end_utc,
        )
        .scalar()
        or 0
    )
    month_refunds = (
        db.query(func.sum(Refund.amount_paise))
        .filter(
            Refund.tenant_id == tenant_id,
            Refund.status == RefundStatus.COMPLETED,
            Refund.created_at >= month_start_utc,
            Refund.created_at <= month_end_utc,
        )
        .scalar()
        or 0
    )
    month_net_paise = max(0, month_gross - month_refunds)

    # Pending invoices and outstanding dues
    pending_statuses = (
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    )
    pending_count = (
        db.query(func.count(Invoice.id))
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_status.in_(pending_statuses),
            Invoice.balance_amount_paise > 0,
        )
        .scalar()
        or 0
    )
    outstanding_paise = (
        db.query(func.sum(Invoice.balance_amount_paise))
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_status.in_(pending_statuses),
            Invoice.balance_amount_paise > 0,
        )
        .scalar()
        or 0
    )

    return FinancialStats(
        total_revenue_paise=total_net_paise,
        total_revenue_rupees=round(total_net_paise / 100.0, 2),
        today_collection_paise=today_net_paise,
        today_collection_rupees=round(today_net_paise / 100.0, 2),
        monthly_collection_paise=month_net_paise,
        monthly_collection_rupees=round(month_net_paise / 100.0, 2),
        pending_payments_count=pending_count,
        outstanding_dues_paise=outstanding_paise,
        outstanding_dues_rupees=round(outstanding_paise / 100.0, 2),
    )


def get_membership_stats(db: Session, tenant_id: uuid.UUID) -> MembershipStats:
    """Calculate membership subscription statistics."""
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()

    active_count = (
        db.query(func.count(Membership.id))
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        .scalar()
        or 0
    )
    expired_count = (
        db.query(func.count(Membership.id))
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.EXPIRED,
        )
        .scalar()
        or 0
    )
    expiring_this_week = (
        db.query(func.count(Membership.id))
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date >= today,
            Membership.end_date <= today + timedelta(days=7),
        )
        .scalar()
        or 0
    )
    upcoming_renewals = (
        db.query(func.count(Membership.id))
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date >= today,
            Membership.end_date <= today + timedelta(days=30),
        )
        .scalar()
        or 0
    )

    return MembershipStats(
        active_memberships=active_count,
        expired_memberships=expired_count,
        expiring_this_week=expiring_this_week,
        upcoming_renewals=upcoming_renewals,
    )


def get_attendance_stats(db: Session, tenant_id: uuid.UUID, days_trend: int = 7) -> AttendanceStats:
    """Calculate attendance stats and daily check-in trend for the last N days."""
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()
    today_start_utc, today_end_utc = _get_time_bounds(tz, today)
    month_start_utc, month_end_utc = _get_month_bounds(tz, today)

    today_check_ins = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.check_in_time >= today_start_utc,
            Attendance.check_in_time <= today_end_utc,
        )
        .scalar()
        or 0
    )
    monthly_attendance = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.tenant_id == tenant_id,
            Attendance.check_in_time >= month_start_utc,
            Attendance.check_in_time <= month_end_utc,
        )
        .scalar()
        or 0
    )

    daily_trends: List[AttendanceDailyTrend] = []
    # Calculate daily count for each of the last `days_trend` days in chronological order
    for offset in range(days_trend - 1, -1, -1):
        target_day = today - timedelta(days=offset)
        d_start, d_end = _get_time_bounds(tz, target_day)
        count = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.tenant_id == tenant_id,
                Attendance.check_in_time >= d_start,
                Attendance.check_in_time <= d_end,
            )
            .scalar()
            or 0
        )
        daily_trends.append(
            AttendanceDailyTrend(
                date=target_day,
                day_name=target_day.strftime("%a"),
                check_ins=count,
            )
        )

    return AttendanceStats(
        today_check_ins=today_check_ins,
        monthly_attendance=monthly_attendance,
        daily_trends=daily_trends,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Activity Feeds
# ──────────────────────────────────────────────────────────────────────────────

def get_recent_payments(db: Session, tenant_id: uuid.UUID, limit: int = 5) -> List[RecentPaymentItem]:
    """Retrieve the most recent successful payment transactions."""
    payments = (
        db.query(Payment)
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_((PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED)),
        )
        .order_by(desc(Payment.payment_date))
        .limit(limit)
        .all()
    )
    result = []
    for p in payments:
        inv = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        mem = db.query(Member).filter(Member.id == inv.member_id).first() if inv else None
        receipt = db.query(Receipt).filter(Receipt.payment_id == p.id).first()
        result.append(
            RecentPaymentItem(
                payment_id=p.id,
                invoice_number=inv.invoice_number if inv else None,
                member_name=mem.full_name if mem else "Unknown",
                member_id=mem.id if mem else uuid.UUID(int=0),
                amount_paise=p.amount_paise,
                amount_rupees=round(p.amount_paise / 100.0, 2),
                payment_method=p.payment_method.value if hasattr(p.payment_method, "value") else str(p.payment_method),
                payment_status=p.payment_status.value if hasattr(p.payment_status, "value") else str(p.payment_status),
                payment_date=p.payment_date,
                receipt_number=receipt.receipt_number if receipt else None,
            )
        )
    return result


def get_upcoming_renewals(db: Session, tenant_id: uuid.UUID, limit: int = 5) -> List[UpcomingRenewalItem]:
    """Retrieve active memberships closest to expiry."""
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()

    memberships = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date >= today,
        )
        .order_by(Membership.end_date.asc())
        .limit(limit)
        .all()
    )
    result = []
    for m in memberships:
        member = db.query(Member).filter(Member.id == m.member_id).first()
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.membership_plan_id).first()
        days_rem = (m.end_date - today).days
        result.append(
            UpcomingRenewalItem(
                membership_id=m.id,
                member_id=m.member_id,
                member_name=member.full_name if member else "Unknown",
                phone=member.phone if member else None,
                plan_name=plan.name if plan else "Unknown Plan",
                end_date=m.end_date,
                days_remaining=days_rem,
            )
        )
    return result


def get_pending_dues(db: Session, tenant_id: uuid.UUID, limit: int = 5) -> List[PendingDueItem]:
    """Retrieve pending invoices with the highest outstanding balance."""
    tz = _get_tenant_tz(db, tenant_id)
    today = datetime.now(tz).date()

    pending_statuses = (
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    )
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_status.in_(pending_statuses),
            Invoice.balance_amount_paise > 0,
        )
        .order_by(desc(Invoice.balance_amount_paise))
        .limit(limit)
        .all()
    )
    result = []
    for inv in invoices:
        member = db.query(Member).filter(Member.id == inv.member_id).first()
        days_overdue = max(0, (today - inv.due_date).days)
        result.append(
            PendingDueItem(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                member_id=inv.member_id,
                member_name=member.full_name if member else "Unknown",
                phone=member.phone if member else None,
                due_date=inv.due_date,
                total_amount_paise=inv.amount_paise,
                balance_amount_paise=inv.balance_amount_paise,
                balance_amount_rupees=round(inv.balance_amount_paise / 100.0, 2),
                days_overdue=days_overdue,
            )
        )
    return result


def get_recent_registrations(db: Session, tenant_id: uuid.UUID, limit: int = 5) -> List[RecentRegistrationItem]:
    """Retrieve latest registered gym members."""
    members = (
        db.query(Member)
        .filter(Member.tenant_id == tenant_id)
        .order_by(desc(Member.created_at))
        .limit(limit)
        .all()
    )
    return [
        RecentRegistrationItem(
            member_id=m.id,
            full_name=m.full_name,
            phone=m.phone,
            email=m.email,
            status=m.status.value if hasattr(m.status, "value") else str(m.status),
            created_at=m.created_at,
        )
        for m in members
    ]


def get_recent_attendance(db: Session, tenant_id: uuid.UUID, limit: int = 5) -> List[RecentAttendanceItem]:
    """Retrieve latest member check-in visits."""
    records = (
        db.query(Attendance)
        .filter(Attendance.tenant_id == tenant_id)
        .order_by(desc(Attendance.check_in_time))
        .limit(limit)
        .all()
    )
    result = []
    for a in records:
        member = db.query(Member).filter(Member.id == a.member_id).first()
        result.append(
            RecentAttendanceItem(
                attendance_id=a.id,
                member_id=a.member_id,
                member_name=member.full_name if member else "Unknown",
                phone=member.phone if member else None,
                check_in_time=a.check_in_time,
                check_out_time=a.check_out_time,
                check_in_method=a.check_in_method.value if hasattr(a.check_in_method, "value") else str(a.check_in_method),
                override_reason=a.override_reason,
            )
        )
    return result


def get_dashboard_summary(db: Session, tenant_id: uuid.UUID) -> DashboardSummaryResponse:
    """Consolidate full dashboard KPIs and recent activity into a single payload."""
    tz = _get_tenant_tz(db, tenant_id)
    now = datetime.now(tz)

    return DashboardSummaryResponse(
        tenant_id=tenant_id,
        as_of=now,
        member_stats=get_member_stats(db, tenant_id),
        financial_stats=get_financial_stats(db, tenant_id),
        membership_stats=get_membership_stats(db, tenant_id),
        attendance_stats=get_attendance_stats(db, tenant_id, days_trend=7),
        recent_payments=get_recent_payments(db, tenant_id, limit=5),
        upcoming_renewals=get_upcoming_renewals(db, tenant_id, limit=5),
        pending_dues=get_pending_dues(db, tenant_id, limit=5),
        recent_registrations=get_recent_registrations(db, tenant_id, limit=5),
        recent_attendance=get_recent_attendance(db, tenant_id, limit=5),
    )

