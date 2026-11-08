"""Reminder service — expiry tracking, renewal worklists, dues ageing, WhatsApp generation, and contact logs."""
import math
import re
import urllib.parse
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.models.membership import Membership, MembershipStatus
from app.models.membership_plan import MembershipPlan
from app.models.invoice import Invoice, InvoiceStatus
from app.models.reminder import (
    ReminderLog,
    ReminderCategory,
    ContactChannel,
    ContactOutcome,
)
from app.schemas.reminders import (
    WhatsAppMessageRequest,
    WhatsAppMessageResponse,
    ExpiryItem,
    ExpiryWorklistResponse,
    RenewalFollowUpItem,
    RenewalWorklistResponse,
    DuesWorklistItem,
    DuesWorklistResponse,
    BirthdayItem,
    BirthdayWorklistResponse,
    ReminderContactCreateRequest,
    ReminderContactResponse,
    ReminderContactListResponse,
    FollowUpItem,
    FollowUpListResponse,
    ReminderSettingsResponse,
    ReminderSettingsUpdateRequest,
)
from app.services.membership_service import get_gym_today, sync_expired_memberships
from app.services.audit_service import log_audit_event


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _clean_phone_number(phone: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Format phone number to WhatsApp international standard without '+' or special characters.
    Defaults to Indian country code (91) for 10-digit mobile numbers.
    Returns (cleaned_digits, is_valid).
    """
    if not phone:
        return None, False

    # Extract digits only
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None, False

    # Strip leading zeros
    digits = digits.lstrip("0")

    # If standard 10-digit Indian mobile number, prepend 91
    if len(digits) == 10:
        digits = "91" + digits

    # Valid international length is between 10 and 15 digits
    is_valid = 10 <= len(digits) <= 15
    return digits if is_valid else digits, is_valid


def _get_member_latest_contact(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
) -> Tuple[Optional[datetime], Optional[str], Optional[date]]:
    """Retrieve the latest contact attempt timestamp, outcome, and scheduled follow-up date."""
    latest = (
        db.query(ReminderLog)
        .filter(
            ReminderLog.tenant_id == tenant_id,
            ReminderLog.member_id == member_id,
        )
        .order_by(ReminderLog.contact_time.desc())
        .first()
    )
    if latest:
        return latest.contact_time, latest.outcome.value, latest.follow_up_date
    return None, None, None


def _get_member_balance_paise(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
) -> int:
    """Calculate member's outstanding balance from active invoices."""
    res = (
        db.query(func.coalesce(func.sum(Invoice.balance_amount_paise), 0))
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.member_id == member_id,
            Invoice.invoice_status != InvoiceStatus.CANCELLED,
        )
        .scalar()
    )
    return int(res or 0)


# ──────────────────────────────────────────────────────────────────────────────
# WhatsApp Click-to-Chat Generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_whatsapp_message(
    db: Session,
    tenant_id: uuid.UUID,
    payload: WhatsAppMessageRequest,
) -> WhatsAppMessageResponse:
    """
    Generate pre-filled message text and safe WhatsApp click-to-chat URL.
    Does NOT send the message automatically.
    """
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this gym",
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    gym_name = tenant.name if tenant else "GYMCORE"

    # Clean phone
    clean_phone, is_valid_phone = _clean_phone_number(member.phone)

    # If custom message provided, use it
    if payload.custom_message:
        message_text = payload.custom_message
    else:
        # Generate default template per category
        if payload.category == ReminderCategory.MEMBERSHIP_EXPIRING:
            # Locate membership
            ms = None
            if payload.membership_id:
                ms = db.query(Membership).filter(Membership.id == payload.membership_id, Membership.tenant_id == tenant_id).first()
            if not ms:
                ms = (
                    db.query(Membership)
                    .filter(Membership.member_id == member.id, Membership.tenant_id == tenant_id)
                    .order_by(Membership.end_date.desc())
                    .first()
                )
            plan_name = ms.membership_plan.name if ms and ms.membership_plan else "gym"
            end_str = ms.end_date.strftime("%d-%b-%Y") if ms else "soon"
            message_text = (
                f"Hi {member.full_name}, this is a friendly reminder from {gym_name} that your {plan_name} "
                f"membership expires on {end_str}. Renew early to continue your fitness journey without interruption!"
            )

        elif payload.category == ReminderCategory.MEMBERSHIP_EXPIRED:
            ms = None
            if payload.membership_id:
                ms = db.query(Membership).filter(Membership.id == payload.membership_id, Membership.tenant_id == tenant_id).first()
            if not ms:
                ms = (
                    db.query(Membership)
                    .filter(Membership.member_id == member.id, Membership.tenant_id == tenant_id)
                    .order_by(Membership.end_date.desc())
                    .first()
                )
            end_str = ms.end_date.strftime("%d-%b-%Y") if ms else "recently"
            message_text = (
                f"Hi {member.full_name}, your membership at {gym_name} expired on {end_str}. "
                f"We miss seeing you! Please visit the front desk or contact us to renew your membership today."
            )

        elif payload.category == ReminderCategory.PAYMENT_DUE:
            inv = None
            if payload.invoice_id:
                inv = db.query(Invoice).filter(Invoice.id == payload.invoice_id, Invoice.tenant_id == tenant_id).first()
            if not inv:
                inv = (
                    db.query(Invoice)
                    .filter(Invoice.member_id == member.id, Invoice.tenant_id == tenant_id, Invoice.balance_amount_paise > 0)
                    .order_by(Invoice.due_date.asc())
                    .first()
                )
            amount_str = f"₹{inv.balance_amount_paise / 100:.2f}" if inv else "pending fees"
            inv_ref = f"(Invoice #{inv.invoice_number})" if inv else ""
            due_str = f" due on {inv.due_date.strftime('%d-%b-%Y')}" if inv else ""
            message_text = (
                f"Hi {member.full_name}, you have an outstanding payment of {amount_str} {inv_ref}{due_str} "
                f"at {gym_name}. Please clear your balance at your earliest convenience."
            )

        elif payload.category == ReminderCategory.RENEWAL_FOLLOWUP:
            message_text = (
                f"Hi {member.full_name}, following up regarding your membership renewal at {gym_name}. "
                f"Let us know if you would like to explore our latest packages or renewal offers!"
            )

        elif payload.category == ReminderCategory.BIRTHDAY:
            message_text = (
                f"Happy Birthday {member.full_name}! 🎂 Wishing you a fantastic year of health, strength, and happiness "
                f"from all of us at {gym_name}!"
            )
        else:
            message_text = f"Hello {member.full_name}, greetings from {gym_name}!"

    whatsapp_url = None
    warning = None
    can_send = False

    if is_valid_phone and clean_phone:
        encoded_msg = urllib.parse.quote(message_text)
        whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
        can_send = True
    else:
        warning = "Member has an invalid or missing contact phone number"

    return WhatsAppMessageResponse(
        category=payload.category,
        member_id=member.id,
        member_name=member.full_name,
        phone=member.phone,
        clean_phone=clean_phone if is_valid_phone else None,
        message_text=message_text,
        whatsapp_url=whatsapp_url,
        can_send=can_send,
        warning=warning,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Membership Expiry Tracking Worklist
# ──────────────────────────────────────────────────────────────────────────────

def get_membership_expiry_worklist(
    db: Session,
    tenant_id: uuid.UUID,
    category: Optional[str] = None,
    warning_days: Optional[int] = None,
    lapsed_days: Optional[int] = None,
    query_str: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> ExpiryWorklistResponse:
    """
    Retrieve members whose subscriptions are expiring soon, today, expired, or lapsed.
    Defaults to tenant's configured lapse grace period and expiry warning window.
    Handles gym timezone and multiple memberships safely.
    """
    sync_expired_memberships(db, tenant_id)
    today = get_gym_today(db, tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    eff_warning_days = warning_days if warning_days is not None else (tenant.membership_expiry_warning_days if tenant else 7)
    eff_lapsed_days = lapsed_days if lapsed_days is not None else (tenant.membership_lapsed_grace_days if tenant else 30)

    # Subquery: get latest membership per member
    latest_sub = (
        db.query(
            Membership.member_id,
            func.max(Membership.end_date).label("max_end_date"),
        )
        .filter(Membership.tenant_id == tenant_id)
        .group_by(Membership.member_id)
        .subquery()
    )

    query = (
        db.query(Membership)
        .join(
            latest_sub,
            (Membership.member_id == latest_sub.c.member_id)
            & (Membership.end_date == latest_sub.c.max_end_date),
        )
        .join(Member, Member.id == Membership.member_id)
        .join(MembershipPlan, MembershipPlan.id == Membership.membership_plan_id)
        .filter(Membership.tenant_id == tenant_id)
    )

    # Search filter
    if query_str:
        q_term = f"%{query_str.strip()}%"
        query = query.filter(
            or_(
                Member.full_name.ilike(q_term),
                Member.phone.ilike(q_term),
                Member.member_code.ilike(q_term),
            )
        )

    # Date filters
    if from_date is not None:
        query = query.filter(Membership.end_date >= from_date)
    if to_date is not None:
        query = query.filter(Membership.end_date <= to_date)

    all_memberships = query.order_by(Membership.end_date.asc()).all()

    items: List[ExpiryItem] = []
    expiring_soon_cnt = 0
    expiring_today_cnt = 0
    expired_cnt = 0
    lapsed_cnt = 0

    for m in all_memberships:
        delta_days = (m.end_date - today).days

        # Determine expiry classification using tenant-configured thresholds
        if delta_days == 0 and m.status == MembershipStatus.ACTIVE:
            cat = "EXPIRING_TODAY"
            expiring_today_cnt += 1
        elif 0 < delta_days <= eff_warning_days and m.status == MembershipStatus.ACTIVE:
            cat = "EXPIRING_SOON"
            expiring_soon_cnt += 1
        elif delta_days < 0 and abs(delta_days) <= eff_lapsed_days:
            cat = "EXPIRED"
            expired_cnt += 1
        elif delta_days < 0 and abs(delta_days) > eff_lapsed_days:
            cat = "LAPSED"
            lapsed_cnt += 1
        else:
            # Active and beyond warning period, or future membership
            continue

        if category and category.upper() != cat:
            continue

        # Balance & contact log
        bal = _get_member_balance_paise(db, tenant_id, m.member_id)
        last_contact, last_outcome, next_followup = _get_member_latest_contact(db, tenant_id, m.member_id)

        items.append(
            ExpiryItem(
                member_id=m.member_id,
                member_name=m.member.full_name,
                member_phone=m.member.phone,
                member_email=m.member.email,
                member_code=m.member.member_code,
                membership_id=m.id,
                plan_name=m.membership_plan.name,
                start_date=m.start_date,
                end_date=m.end_date,
                membership_status=m.status.value,
                days_until_expiry=delta_days,
                expiry_category=cat,
                outstanding_balance_paise=bal,
                last_contact_date=last_contact,
                last_contact_outcome=last_outcome,
                next_follow_up_date=next_followup,
            )
        )

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_items = items[offset : offset + page_size]

    return ExpiryWorklistResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
        expiring_soon_count=expiring_soon_cnt,
        expiring_today_count=expiring_today_cnt,
        expired_count=expired_cnt,
        lapsed_count=lapsed_cnt,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Renewal Follow-Up Worklist
# ──────────────────────────────────────────────────────────────────────────────

def get_renewal_followup_worklist(
    db: Session,
    tenant_id: uuid.UUID,
    status_filter: Optional[str] = None,
    query_str: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> RenewalWorklistResponse:
    """Retrieve members needing renewal outreach with contact histories and pending follow-ups."""
    sync_expired_memberships(db, tenant_id)
    today = get_gym_today(db, tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    warning_window = tenant.membership_expiry_warning_days if tenant else 7

    # Subquery: member's latest membership end date
    latest_sub = (
        db.query(
            Membership.member_id,
            func.max(Membership.end_date).label("max_end_date"),
        )
        .filter(Membership.tenant_id == tenant_id)
        .group_by(Membership.member_id)
        .subquery()
    )

    query = (
        db.query(Membership)
        .join(
            latest_sub,
            (Membership.member_id == latest_sub.c.member_id)
            & (Membership.end_date == latest_sub.c.max_end_date),
        )
        .join(Member, Member.id == Membership.member_id)
        .join(MembershipPlan, MembershipPlan.id == Membership.membership_plan_id)
        .filter(Membership.tenant_id == tenant_id)
    )

    if query_str:
        q_term = f"%{query_str.strip()}%"
        query = query.filter(
            or_(
                Member.full_name.ilike(q_term),
                Member.phone.ilike(q_term),
                Member.member_code.ilike(q_term),
            )
        )

    if from_date is not None:
        query = query.filter(Membership.end_date >= from_date)
    if to_date is not None:
        query = query.filter(Membership.end_date <= to_date)

    memberships = query.order_by(Membership.end_date.asc()).all()

    items: List[RenewalFollowUpItem] = []
    for m in memberships:
        # A member requires renewal outreach if their membership is expired or expiring within gym's warning window
        delta_days = (m.end_date - today).days
        if delta_days > warning_window and m.status == MembershipStatus.ACTIVE:
            continue

        bal = _get_member_balance_paise(db, tenant_id, m.member_id)
        last_contact, last_outcome, next_followup = _get_member_latest_contact(db, tenant_id, m.member_id)

        follow_up_status = "NONE"
        if next_followup:
            if next_followup < today:
                follow_up_status = "OVERDUE"
            else:
                follow_up_status = "PENDING"

        if status_filter and follow_up_status != status_filter.upper():
            continue

        items.append(
            RenewalFollowUpItem(
                member_id=m.member_id,
                member_name=m.member.full_name,
                member_phone=m.member.phone,
                member_email=m.member.email,
                member_code=m.member.member_code,
                membership_id=m.id,
                plan_name=m.membership_plan.name,
                start_date=m.start_date,
                end_date=m.end_date,
                membership_status=m.status.value,
                outstanding_balance_paise=bal,
                last_contact_date=last_contact,
                last_contact_outcome=last_outcome,
                next_follow_up_date=next_followup,
                follow_up_status=follow_up_status,
            )
        )

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_items = items[offset : offset + page_size]

    return RenewalWorklistResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Outstanding Dues Worklist
# ──────────────────────────────────────────────────────────────────────────────

def get_outstanding_dues_worklist(
    db: Session,
    tenant_id: uuid.UUID,
    ageing: Optional[str] = None,
    query_str: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> DuesWorklistResponse:
    """
    Retrieve unpaid or partially-paid invoices with overdue ageing breakdown.
    Excludes fully paid and cancelled invoices.
    """
    today = get_gym_today(db, tenant_id)

    query = (
        db.query(Invoice)
        .join(Member, Member.id == Invoice.member_id)
        .outerjoin(Membership, Membership.id == Invoice.membership_id)
        .outerjoin(MembershipPlan, MembershipPlan.id == Membership.membership_plan_id)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_status != InvoiceStatus.CANCELLED,
            Invoice.balance_amount_paise > 0,
        )
    )

    if query_str:
        q_term = f"%{query_str.strip()}%"
        query = query.filter(
            or_(
                Member.full_name.ilike(q_term),
                Member.phone.ilike(q_term),
                Member.member_code.ilike(q_term),
                Invoice.invoice_number.ilike(q_term),
            )
        )

    if from_date is not None:
        query = query.filter(Invoice.due_date >= from_date)
    if to_date is not None:
        query = query.filter(Invoice.due_date <= to_date)

    invoices = query.order_by(Invoice.due_date.asc()).all()

    items: List[DuesWorklistItem] = []
    total_dues_paise = 0
    days_0_7_paise = 0
    days_8_30_paise = 0
    days_over_30_paise = 0

    for inv in invoices:
        overdue_days = max(0, (today - inv.due_date).days)
        total_dues_paise += inv.balance_amount_paise

        if overdue_days <= 7:
            ageing_cat = "0-7 days"
            days_0_7_paise += inv.balance_amount_paise
        elif overdue_days <= 30:
            ageing_cat = "8-30 days"
            days_8_30_paise += inv.balance_amount_paise
        else:
            ageing_cat = "30+ days"
            days_over_30_paise += inv.balance_amount_paise

        if ageing and ageing.strip() != ageing_cat:
            continue

        last_contact, last_outcome, next_followup = _get_member_latest_contact(db, tenant_id, inv.member_id)
        plan_name = inv.membership.membership_plan.name if inv.membership and inv.membership.membership_plan else None

        items.append(
            DuesWorklistItem(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                member_id=inv.member_id,
                member_name=inv.member.full_name,
                member_phone=inv.member.phone,
                member_code=inv.member.member_code,
                membership_id=inv.membership_id,
                plan_name=plan_name,
                issue_date=inv.issue_date,
                due_date=inv.due_date,
                amount_paise=inv.amount_paise,
                paid_amount_paise=inv.paid_amount_paise,
                balance_amount_paise=inv.balance_amount_paise,
                invoice_status=inv.invoice_status.value,
                days_overdue=overdue_days,
                ageing_category=ageing_cat,
                last_contact_date=last_contact,
                last_contact_outcome=last_outcome,
                next_follow_up_date=next_followup,
            )
        )

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_items = items[offset : offset + page_size]

    return DuesWorklistResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
        total_dues_paise=total_dues_paise,
        days_0_7_paise=days_0_7_paise,
        days_8_30_paise=days_8_30_paise,
        days_over_30_paise=days_over_30_paise,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Birthday Reminders Worklist
# ──────────────────────────────────────────────────────────────────────────────

def get_birthday_reminders_worklist(
    db: Session,
    tenant_id: uuid.UUID,
    upcoming_days: int = 7,
    is_today_only: bool = False,
    query_str: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> BirthdayWorklistResponse:
    """Identify members with birthdays occurring today or within upcoming window."""
    today = get_gym_today(db, tenant_id)

    query = db.query(Member).filter(
        Member.tenant_id == tenant_id,
        Member.date_of_birth.isnot(None),
    )

    if query_str:
        q_term = f"%{query_str.strip()}%"
        query = query.filter(
            or_(
                Member.full_name.ilike(q_term),
                Member.phone.ilike(q_term),
                Member.member_code.ilike(q_term),
            )
        )

    members = query.all()

    items: List[BirthdayItem] = []
    today_cnt = 0
    upcoming_cnt = 0

    for m in members:
        dob = m.date_of_birth
        if not dob:
            continue

        # Calculate next birthday
        try:
            bday_this_year = date(today.year, dob.month, dob.day)
        except ValueError:
            # Handle leap year Feb 29 for non-leap years
            bday_this_year = date(today.year, 2, 28)

        if bday_this_year < today:
            try:
                next_bday = date(today.year + 1, dob.month, dob.day)
            except ValueError:
                next_bday = date(today.year + 1, 2, 28)
        else:
            next_bday = bday_this_year

        days_until = (next_bday - today).days
        is_today = days_until == 0

        if is_today:
            today_cnt += 1
        elif days_until <= upcoming_days:
            upcoming_cnt += 1

        if is_today_only and not is_today:
            continue

        if days_until > upcoming_days:
            continue

        turning_age = next_bday.year - dob.year
        last_contact, _, _ = _get_member_latest_contact(db, tenant_id, m.id)

        items.append(
            BirthdayItem(
                member_id=m.id,
                member_name=m.full_name,
                member_phone=m.phone,
                member_code=m.member_code,
                date_of_birth=dob,
                next_birthday=next_bday,
                days_until_birthday=days_until,
                turning_age=turning_age,
                is_today=is_today,
                membership_status=m.status.value,
                last_contact_date=last_contact,
            )
        )

    # Sort items by days until birthday
    items.sort(key=lambda x: x.days_until_birthday)

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_items = items[offset : offset + page_size]

    return BirthdayWorklistResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
        today_birthdays_count=today_cnt,
        upcoming_birthdays_count=upcoming_cnt,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Contact Logging & Follow-up Management
# ──────────────────────────────────────────────────────────────────────────────

def create_reminder_contact(
    db: Session,
    tenant_id: uuid.UUID,
    payload: ReminderContactCreateRequest,
    staff_user: User,
) -> ReminderLog:
    """Record a verified reminder contact attempt or follow-up note."""
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this gym",
        )

    contact_time = payload.contact_time or datetime.now(timezone.utc)

    log = ReminderLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=payload.member_id,
        staff_user_id=staff_user.id,
        category=payload.category,
        channel=payload.channel,
        outcome=payload.outcome,
        message_snippet=payload.message_snippet,
        notes=payload.notes,
        contact_time=contact_time,
        follow_up_date=payload.follow_up_date,
    )

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _to_reminder_contact_response(log: ReminderLog) -> ReminderContactResponse:
    return ReminderContactResponse(
        id=log.id,
        tenant_id=log.tenant_id,
        member_id=log.member_id,
        member_name=log.member.full_name if log.member else None,
        member_phone=log.member.phone if log.member else None,
        staff_user_id=log.staff_user_id,
        staff_user_name=log.staff_user.name if log.staff_user else None,
        category=log.category,
        channel=log.channel,
        outcome=log.outcome,
        message_snippet=log.message_snippet,
        notes=log.notes,
        contact_time=log.contact_time,
        follow_up_date=log.follow_up_date,
        created_at=log.created_at,
    )


def list_reminder_contacts(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: Optional[uuid.UUID] = None,
    staff_user_id: Optional[uuid.UUID] = None,
    category: Optional[ReminderCategory] = None,
    outcome: Optional[ContactOutcome] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> ReminderContactListResponse:
    """Retrieve paginated contact logs with optional filters."""
    query = db.query(ReminderLog).filter(ReminderLog.tenant_id == tenant_id)

    if member_id is not None:
        query = query.filter(ReminderLog.member_id == member_id)
    if staff_user_id is not None:
        query = query.filter(ReminderLog.staff_user_id == staff_user_id)
    if category is not None:
        query = query.filter(ReminderLog.category == category)
    if outcome is not None:
        query = query.filter(ReminderLog.outcome == outcome)

    if from_date is not None:
        dt_start = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
        query = query.filter(ReminderLog.contact_time >= dt_start)
    if to_date is not None:
        dt_end = datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)
        query = query.filter(ReminderLog.contact_time <= dt_end)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size

    records = (
        query.order_by(ReminderLog.contact_time.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [_to_reminder_contact_response(r) for r in records]
    return ReminderContactListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


def get_follow_ups(
    db: Session,
    tenant_id: uuid.UUID,
    staff_user_id: Optional[uuid.UUID] = None,
    is_overdue: Optional[bool] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> FollowUpListResponse:
    """
    Retrieve active follow-ups scheduled across members.
    Identifies overdue vs due today vs upcoming follow-ups.
    """
    today = get_gym_today(db, tenant_id)

    query = (
        db.query(ReminderLog)
        .filter(
            ReminderLog.tenant_id == tenant_id,
            ReminderLog.follow_up_date.isnot(None),
        )
    )

    if staff_user_id is not None:
        query = query.filter(ReminderLog.staff_user_id == staff_user_id)
    if from_date is not None:
        query = query.filter(ReminderLog.follow_up_date >= from_date)
    if to_date is not None:
        query = query.filter(ReminderLog.follow_up_date <= to_date)

    if is_overdue is not None:
        if is_overdue:
            query = query.filter(ReminderLog.follow_up_date < today)
        else:
            query = query.filter(ReminderLog.follow_up_date >= today)

    records = query.order_by(ReminderLog.follow_up_date.asc()).all()

    items: List[FollowUpItem] = []
    overdue_cnt = 0
    today_cnt = 0
    upcoming_cnt = 0

    for r in records:
        days_diff = (today - r.follow_up_date).days
        overdue_flag = r.follow_up_date < today

        if r.follow_up_date < today:
            overdue_cnt += 1
        elif r.follow_up_date == today:
            today_cnt += 1
        else:
            upcoming_cnt += 1

        items.append(
            FollowUpItem(
                contact_log_id=r.id,
                member_id=r.member_id,
                member_name=r.member.full_name if r.member else "Unknown",
                member_phone=r.member.phone if r.member else None,
                staff_user_id=r.staff_user_id,
                staff_user_name=r.staff_user.name if r.staff_user else None,
                category=r.category,
                last_channel=r.channel,
                last_outcome=r.outcome,
                last_contact_time=r.contact_time,
                follow_up_date=r.follow_up_date,
                days_overdue=days_diff,
                is_overdue=overdue_flag,
                notes=r.notes,
            )
        )

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_items = items[offset : offset + page_size]

    return FollowUpListResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
        overdue_count=overdue_cnt,
        due_today_count=today_cnt,
        upcoming_count=upcoming_cnt,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Gym Reminder & Expiry Policy Settings
# ──────────────────────────────────────────────────────────────────────────────

def get_reminder_settings(db: Session, tenant_id: uuid.UUID) -> ReminderSettingsResponse:
    """Retrieve gym's configured lapse grace period and expiry warning thresholds."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return ReminderSettingsResponse(
        tenant_id=tenant.id,
        membership_lapsed_grace_days=tenant.membership_lapsed_grace_days,
        membership_expiry_warning_days=tenant.membership_expiry_warning_days,
    )


def update_reminder_settings(
    db: Session,
    tenant_id: uuid.UUID,
    payload: ReminderSettingsUpdateRequest,
    current_user: Optional[User] = None,
) -> ReminderSettingsResponse:
    """Update gym-level lapse grace period and expiry warning settings (OWNER / MANAGER only)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    before_values = {
        "membership_lapsed_grace_days": tenant.membership_lapsed_grace_days,
        "membership_expiry_warning_days": tenant.membership_expiry_warning_days,
    }

    if payload.membership_lapsed_grace_days is not None:
        tenant.membership_lapsed_grace_days = payload.membership_lapsed_grace_days
    if payload.membership_expiry_warning_days is not None:
        tenant.membership_expiry_warning_days = payload.membership_expiry_warning_days

    after_values = {
        "membership_lapsed_grace_days": tenant.membership_lapsed_grace_days,
        "membership_expiry_warning_days": tenant.membership_expiry_warning_days,
    }

    log_audit_event(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id if current_user else None,
        action="SETTINGS_UPDATE",
        resource_type="TENANT",
        resource_id=str(tenant.id),
        before_values=before_values,
        after_values=after_values,
        reason="Gym reminder & expiry settings updated",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return ReminderSettingsResponse(
        tenant_id=tenant.id,
        membership_lapsed_grace_days=tenant.membership_lapsed_grace_days,
        membership_expiry_warning_days=tenant.membership_expiry_warning_days,
    )


