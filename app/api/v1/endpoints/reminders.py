"""Reminder and Follow-up REST API endpoints."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.auth import require_role
from app.core.database import get_db
from app.models.reminder import ReminderCategory, ContactOutcome
from app.models.user import User, UserRole
from app.schemas.reminders import (
    WhatsAppMessageRequest,
    WhatsAppMessageResponse,
    ExpiryWorklistResponse,
    RenewalWorklistResponse,
    DuesWorklistResponse,
    BirthdayWorklistResponse,
    ReminderContactCreateRequest,
    ReminderContactResponse,
    ReminderContactListResponse,
    FollowUpListResponse,
    ReminderSettingsResponse,
    ReminderSettingsUpdateRequest,
)
from app.services import reminder_service

router = APIRouter()

_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_MANAGE_ROLES = (UserRole.OWNER, UserRole.MANAGER)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Expiry Tracking Worklist
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/expiries",
    response_model=ExpiryWorklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Membership Expiry Worklist",
    description="Retrieve members whose memberships are expiring soon, today, expired, or lapsed. Defaults to gym's configured thresholds.",
)
async def get_membership_expiry_worklist(
    category: Optional[str] = Query(None, description="Filter: EXPIRING_SOON, EXPIRING_TODAY, EXPIRED, LAPSED"),
    warning_days: Optional[int] = Query(None, ge=1, le=60, description="Optional override for warning threshold days (defaults to gym setting)"),
    lapsed_days: Optional[int] = Query(None, ge=1, le=365, description="Optional override for lapse grace days (defaults to gym setting)"),
    q: Optional[str] = Query(None, description="Search by member name, phone, or code"),
    from_date: Optional[date] = Query(None, description="Filter end_date on or after"),
    to_date: Optional[date] = Query(None, description="Filter end_date on or before"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ExpiryWorklistResponse:
    return reminder_service.get_membership_expiry_worklist(
        db=db,
        tenant_id=current_user.tenant_id,
        category=category,
        warning_days=warning_days,
        lapsed_days=lapsed_days,
        query_str=q,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Renewal Follow-Up Worklist
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/renewals",
    response_model=RenewalWorklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Renewal Follow-up Worklist",
    description="Retrieve members requiring renewal outreach with previous outcomes and follow-up schedules.",
)
async def get_renewal_followup_worklist(
    status_filter: Optional[str] = Query(None, description="Filter by follow-up status: OVERDUE, PENDING, NONE"),
    q: Optional[str] = Query(None, description="Search by member name, phone, or code"),
    from_date: Optional[date] = Query(None, description="Filter end_date on or after"),
    to_date: Optional[date] = Query(None, description="Filter end_date on or before"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> RenewalWorklistResponse:
    return reminder_service.get_renewal_followup_worklist(
        db=db,
        tenant_id=current_user.tenant_id,
        status_filter=status_filter,
        query_str=q,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 3. Outstanding Dues Worklist
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dues",
    response_model=DuesWorklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Outstanding Dues Reminder Worklist",
    description="Identify members with outstanding payments categorized by ageing (0-7, 8-30, 30+ days).",
)
async def get_outstanding_dues_worklist(
    ageing: Optional[str] = Query(None, description="Ageing category: '0-7 days', '8-30 days', '30+ days'"),
    q: Optional[str] = Query(None, description="Search by member name, phone, code, or invoice number"),
    from_date: Optional[date] = Query(None, description="Filter due_date on or after"),
    to_date: Optional[date] = Query(None, description="Filter due_date on or before"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> DuesWorklistResponse:
    return reminder_service.get_outstanding_dues_worklist(
        db=db,
        tenant_id=current_user.tenant_id,
        ageing=ageing,
        query_str=q,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. Birthday Reminders Worklist
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/birthdays",
    response_model=BirthdayWorklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Birthday Reminders Worklist",
    description="Retrieve members with birthdays today or upcoming within the specified window.",
)
async def get_birthday_reminders_worklist(
    upcoming_days: int = Query(7, ge=1, le=30, description="Upcoming days lookahead window"),
    is_today_only: bool = Query(False, description="Filter strictly for birthdays occurring today"),
    q: Optional[str] = Query(None, description="Search by member name, phone, or code"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> BirthdayWorklistResponse:
    return reminder_service.get_birthday_reminders_worklist(
        db=db,
        tenant_id=current_user.tenant_id,
        upcoming_days=upcoming_days,
        is_today_only=is_today_only,
        query_str=q,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 5. WhatsApp Click-to-Chat Generation
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/whatsapp/generate",
    response_model=WhatsAppMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Pre-Filled WhatsApp Message & Link",
    description="Builds ready-to-send WhatsApp template message and click-to-chat URL for staff manual review.",
)
async def generate_whatsapp_message(
    payload: WhatsAppMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> WhatsAppMessageResponse:
    return reminder_service.generate_whatsapp_message(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 6. Contact Logging
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/contacts",
    response_model=ReminderContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log Reminder Contact Interaction",
    description="Record an actual communication attempt with outcome, channel, notes, and optional follow-up date.",
)
async def log_reminder_contact(
    payload: ReminderContactCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ReminderContactResponse:
    log = reminder_service.create_reminder_contact(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
        staff_user=current_user,
    )
    return reminder_service._to_reminder_contact_response(log)


@router.get(
    "/contacts",
    response_model=ReminderContactListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Reminder Contact History",
    description="Query historical reminder communications filtered by member, staff, category, or outcome.",
)
async def list_reminder_contacts(
    member_id: Optional[UUID] = Query(None, description="Filter by member UUID"),
    staff_user_id: Optional[UUID] = Query(None, description="Filter by staff user UUID"),
    category: Optional[ReminderCategory] = Query(None, description="Filter by category"),
    outcome: Optional[ContactOutcome] = Query(None, description="Filter by outcome"),
    from_date: Optional[date] = Query(None, description="Contact on or after YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Contact on or before YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ReminderContactListResponse:
    return reminder_service.list_reminder_contacts(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        staff_user_id=staff_user_id,
        category=category,
        outcome=outcome,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/contacts/member/{member_id}",
    response_model=ReminderContactListResponse,
    status_code=status.HTTP_200_OK,
    summary="Member's Reminder Contact History",
    description="Retrieve all historical contact logs for a specific member.",
)
async def get_member_contact_history(
    member_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ReminderContactListResponse:
    return reminder_service.list_reminder_contacts(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 7. Follow-up Management
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/follow-ups",
    response_model=FollowUpListResponse,
    status_code=status.HTTP_200_OK,
    summary="Scheduled Follow-up Tasks",
    description="Retrieve pending and overdue follow-up interactions across gym members.",
)
async def get_scheduled_follow_ups(
    staff_user_id: Optional[UUID] = Query(None, description="Filter by assigned staff user UUID"),
    is_overdue: Optional[bool] = Query(None, description="Filter strictly overdue tasks"),
    from_date: Optional[date] = Query(None, description="Follow-up date on or after YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Follow-up date on or before YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> FollowUpListResponse:
    return reminder_service.get_follow_ups(
        db=db,
        tenant_id=current_user.tenant_id,
        staff_user_id=staff_user_id,
        is_overdue=is_overdue,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 8. Gym Reminder Settings Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/settings",
    response_model=ReminderSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Gym Reminder Settings",
    description="Retrieve gym-level lapse grace period and expiry warning configuration.",
)
async def get_reminder_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> ReminderSettingsResponse:
    return reminder_service.get_reminder_settings(
        db=db,
        tenant_id=current_user.tenant_id,
    )


@router.patch(
    "/settings",
    response_model=ReminderSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Gym Reminder Settings",
    description="Update gym-level lapse grace period and expiry warning thresholds (OWNER / MANAGER only).",
)
async def update_reminder_settings(
    payload: ReminderSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> ReminderSettingsResponse:
    return reminder_service.update_reminder_settings(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )


