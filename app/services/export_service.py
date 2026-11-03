"""Export service — business logic for CSV and Excel (.xlsx) file generation."""
import io
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.member import Member
from app.models.membership import Membership, MembershipStatus
from app.models.membership_plan import MembershipPlan
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.receipt import Receipt
from app.models.attendance import Attendance, CheckInMethod
from app.services.report_service import (
    generate_revenue_report,
    generate_membership_report,
    generate_attendance_report,
    generate_pending_dues_report,
    generate_expiry_report,
)


def _render_file(df: pd.DataFrame, filename_base: str, export_format: str) -> Tuple[bytes, str, str]:
    """Convert DataFrame into downloadable bytes (CSV or XLSX) with media type and filename."""
    fmt = export_format.strip().lower()
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "csv":
        csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        media_type = "text/csv"
        filename = f"{filename_base}_{timestamp_str}.csv"
        return csv_bytes, media_type, filename
    elif fmt in ("xlsx", "excel"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Export")
        buf.seek(0)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{filename_base}_{timestamp_str}.xlsx"
        return buf.getvalue(), media_type, filename
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{export_format}'. Allowed: 'csv', 'xlsx'",
        )


# ──────────────────────────────────────────────────────────────────────────────
# 1. Member Records Export
# ──────────────────────────────────────────────────────────────────────────────

def export_members(
    db: Session,
    tenant_id: uuid.UUID,
    is_active: Optional[bool] = None,
    export_format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export member records for the tenant."""
    query = db.query(Member).filter(Member.tenant_id == tenant_id)
    if is_active is not None:
        query = query.filter(Member.status == ("ACTIVE" if is_active else "INACTIVE"))

    members = query.order_by(desc(Member.created_at)).all()

    data = []
    for m in members:
        data.append({
            "Member ID": str(m.id),
            "Full Name": m.full_name,
            "Phone": m.phone or "",
            "Email": m.email or "",
            "Gender": m.gender.value if m.gender else "",
            "Date of Birth": str(m.date_of_birth) if m.date_of_birth else "",
            "Status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "Address": m.address or "",
            "Emergency Contact": m.emergency_contact_name or "",
            "Emergency Phone": m.emergency_contact_phone or "",
            "Registered At": m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else "",
        })

    cols = [
        "Member ID", "Full Name", "Phone", "Email", "Gender",
        "Date of Birth", "Status", "Address", "Emergency Contact",
        "Emergency Phone", "Registered At",
    ]
    df = pd.DataFrame(data, columns=cols)
    return _render_file(df, "members_export", export_format)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Membership Records Export
# ──────────────────────────────────────────────────────────────────────────────

def export_memberships(
    db: Session,
    tenant_id: uuid.UUID,
    status_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    export_format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export membership records for the tenant."""
    query = db.query(Membership).filter(Membership.tenant_id == tenant_id)
    if status_filter:
        try:
            st = MembershipStatus[status_filter.upper()]
            query = query.filter(Membership.status == st)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status_filter}")

    if start_date:
        query = query.filter(Membership.start_date >= start_date)
    if end_date:
        query = query.filter(Membership.start_date <= end_date)

    memberships = query.order_by(desc(Membership.created_at)).all()

    data = []
    for m in memberships:
        mem = db.query(Member).filter(Member.id == m.member_id).first()
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.membership_plan_id).first()
        data.append({
            "Membership ID": str(m.id),
            "Member Name": mem.full_name if mem else "Unknown",
            "Member Phone": mem.phone if mem else "",
            "Plan Name": plan.name if plan else "Unknown Plan",
            "Start Date": str(m.start_date),
            "End Date": str(m.end_date),
            "Status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "Plan Price (INR)": f"{float(plan.price):.2f}" if plan and plan.price is not None else "0.00",
            "Notes": m.notes or "",
        })

    cols = [
        "Membership ID", "Member Name", "Member Phone", "Plan Name",
        "Start Date", "End Date", "Status", "Plan Price (INR)", "Notes",
    ]
    df = pd.DataFrame(data, columns=cols)
    return _render_file(df, "memberships_export", export_format)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Payment & Collection Records Export
# ──────────────────────────────────────────────────────────────────────────────

def export_payments(
    db: Session,
    tenant_id: uuid.UUID,
    payment_method: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    export_format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export payment transactions for the tenant."""
    tz_str = db.query(Tenant.timezone).filter(Tenant.id == tenant_id).scalar() or "Asia/Kolkata"
    tz = ZoneInfo(tz_str)

    query = db.query(Payment).filter(Payment.tenant_id == tenant_id)
    if payment_method:
        try:
            pm = PaymentMethod[payment_method.upper()]
            query = query.filter(Payment.payment_method == pm)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment method: {payment_method}")

    if start_date:
        start_utc = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Payment.payment_date >= start_utc)
    if end_date:
        end_utc = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Payment.payment_date <= end_utc)

    payments = query.order_by(desc(Payment.payment_date)).all()

    data = []
    for p in payments:
        inv = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        mem = db.query(Member).filter(Member.id == inv.member_id).first() if inv else None
        receipt = db.query(Receipt).filter(Receipt.payment_id == p.id).first()
        data.append({
            "Payment ID": str(p.id),
            "Receipt Number": receipt.receipt_number if receipt else "",
            "Invoice Number": inv.invoice_number if inv else "",
            "Member Name": mem.full_name if mem else "Unknown",
            "Member Phone": mem.phone if mem else "",
            "Amount (INR)": f"{p.amount_paise / 100.0:.2f}",
            "Payment Method": p.payment_method.value if hasattr(p.payment_method, "value") else str(p.payment_method),
            "Status": p.payment_status.value if hasattr(p.payment_status, "value") else str(p.payment_status),
            "Payment Date": p.payment_date.strftime("%Y-%m-%d %H:%M:%S") if p.payment_date else "",
            "Reference": p.transaction_reference or "",
            "Notes": p.notes or "",
        })

    cols = [
        "Payment ID", "Receipt Number", "Invoice Number", "Member Name", "Member Phone",
        "Amount (INR)", "Payment Method", "Status", "Payment Date", "Reference", "Notes",
    ]
    df = pd.DataFrame(data, columns=cols)
    return _render_file(df, "payments_export", export_format)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Attendance Records Export
# ──────────────────────────────────────────────────────────────────────────────

def export_attendance(
    db: Session,
    tenant_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    member_id: Optional[uuid.UUID] = None,
    export_format: str = "csv",
) -> Tuple[bytes, str, str]:
    """Export attendance visit records for the tenant."""
    tz_str = db.query(Tenant.timezone).filter(Tenant.id == tenant_id).scalar() or "Asia/Kolkata"
    tz = ZoneInfo(tz_str)

    query = db.query(Attendance).filter(Attendance.tenant_id == tenant_id)
    if member_id:
        query = query.filter(Attendance.member_id == member_id)
    if start_date:
        start_utc = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Attendance.check_in_time >= start_utc)
    if end_date:
        end_utc = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz).astimezone(timezone.utc)
        query = query.filter(Attendance.check_in_time <= end_utc)

    visits = query.order_by(desc(Attendance.check_in_time)).all()

    data = []
    for a in visits:
        mem = db.query(Member).filter(Member.id == a.member_id).first()
        data.append({
            "Attendance ID": str(a.id),
            "Member Name": mem.full_name if mem else "Unknown",
            "Member Phone": mem.phone if mem else "",
            "Check-in Time": a.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_in_time else "",
            "Check-out Time": a.check_out_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_out_time else "",
            "Check-in Method": a.check_in_method.value if hasattr(a.check_in_method, "value") else str(a.check_in_method),
            "Override Reason": a.override_reason or "",
        })

    cols = [
        "Attendance ID", "Member Name", "Member Phone", "Check-in Time",
        "Check-out Time", "Check-in Method", "Override Reason",
    ]
    df = pd.DataFrame(data, columns=cols)
    return _render_file(df, "attendance_export", export_format)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Reports Export
# ──────────────────────────────────────────────────────────────────────────────

def export_report(
    db: Session,
    tenant_id: uuid.UUID,
    report_type: str,
    export_format: str = "csv",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    filter_val: Optional[str] = None,
) -> Tuple[bytes, str, str]:
    """Export formatted tabular report data in CSV or Excel format."""
    rep = report_type.strip().lower()
    today = date.today()

    if rep in ("revenue", "collections"):
        sd = start_date or today.replace(day=1)
        ed = end_date or today
        res = generate_revenue_report(db, tenant_id, sd, ed, payment_method=filter_val)
        data = [
            {
                "Payment ID": str(t.payment_id),
                "Invoice Number": t.invoice_number or "",
                "Receipt Number": t.receipt_number or "",
                "Member Name": t.member_name,
                "Amount (INR)": f"{t.amount_rupees:.2f}",
                "Payment Method": t.payment_method,
                "Status": t.payment_status,
                "Payment Date": t.payment_date.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for t in res.transactions
        ]
        cols = ["Payment ID", "Invoice Number", "Receipt Number", "Member Name", "Amount (INR)", "Payment Method", "Status", "Payment Date"]
        df = pd.DataFrame(data, columns=cols)
        return _render_file(df, "revenue_report", export_format)

    elif rep in ("memberships", "membership"):
        res = generate_membership_report(db, tenant_id, start_date=start_date, end_date=end_date, status_filter=filter_val)
        data = [
            {
                "Membership ID": str(m.membership_id),
                "Member Name": m.member_name,
                "Member Phone": m.member_phone or "",
                "Plan Name": m.plan_name,
                "Start Date": str(m.start_date),
                "End Date": str(m.end_date),
                "Status": m.status,
                "Price (INR)": f"{m.price_rupees:.2f}",
            }
            for m in res.memberships
        ]
        cols = ["Membership ID", "Member Name", "Member Phone", "Plan Name", "Start Date", "End Date", "Status", "Price (INR)"]
        df = pd.DataFrame(data, columns=cols)
        return _render_file(df, "membership_report", export_format)

    elif rep in ("attendance", "visits"):
        sd = start_date or today.replace(day=1)
        ed = end_date or today
        res = generate_attendance_report(db, tenant_id, sd, ed, check_in_method=filter_val)
        data = [
            {
                "Attendance ID": str(v.attendance_id),
                "Member Name": v.member_name,
                "Member Phone": v.member_phone or "",
                "Check-in Time": v.check_in_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Check-out Time": v.check_out_time.strftime("%Y-%m-%d %H:%M:%S") if v.check_out_time else "",
                "Method": v.check_in_method,
                "Override Reason": v.override_reason or "",
            }
            for v in res.visits
        ]
        cols = ["Attendance ID", "Member Name", "Member Phone", "Check-in Time", "Check-out Time", "Method", "Override Reason"]
        df = pd.DataFrame(data, columns=cols)
        return _render_file(df, "attendance_report", export_format)

    elif rep in ("pending-dues", "dues"):
        res = generate_pending_dues_report(db, tenant_id, ageing_bucket=filter_val)
        data = [
            {
                "Invoice ID": str(i.invoice_id),
                "Invoice Number": i.invoice_number,
                "Member Name": i.member_name,
                "Member Phone": i.member_phone or "",
                "Issue Date": str(i.issue_date),
                "Due Date": str(i.due_date),
                "Total (INR)": f"{i.total_amount_paise / 100.0:.2f}",
                "Paid (INR)": f"{i.paid_amount_paise / 100.0:.2f}",
                "Balance (INR)": f"{i.balance_amount_rupees:.2f}",
                "Days Overdue": i.days_overdue,
                "Status": i.status,
                "Ageing Bucket": i.ageing_bucket,
            }
            for i in res.invoices
        ]
        cols = ["Invoice ID", "Invoice Number", "Member Name", "Member Phone", "Issue Date", "Due Date", "Total (INR)", "Paid (INR)", "Balance (INR)", "Days Overdue", "Status", "Ageing Bucket"]
        df = pd.DataFrame(data, columns=cols)
        return _render_file(df, "pending_dues_report", export_format)

    elif rep in ("expiries", "expiry"):
        res = generate_expiry_report(db, tenant_id, start_date=start_date, end_date=end_date, status_filter=filter_val)
        data = [
            {
                "Membership ID": str(i.membership_id),
                "Member Name": i.member_name,
                "Member Phone": i.member_phone or "",
                "Plan Name": i.plan_name,
                "End Date": str(i.end_date),
                "Days Remaining": i.days_remaining,
                "Category": i.status,
            }
            for i in res.items
        ]
        cols = ["Membership ID", "Member Name", "Member Phone", "Plan Name", "End Date", "Days Remaining", "Category"]
        df = pd.DataFrame(data, columns=cols)
        return _render_file(df, "expiries_report", export_format)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown report type: '{report_type}'. Allowed: revenue, memberships, attendance, pending-dues, expiries",
        )

