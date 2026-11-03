"""Pydantic schemas for Expiry Tracking, Reminder Worklists, WhatsApp Links, and Follow-up Management."""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.reminder import ReminderCategory, ContactChannel, ContactOutcome


# ──────────────────────────────────────────────────────────────────────────────
# WhatsApp Click-to-Chat Generation Schemas
# ──────────────────────────────────────────────────────────────────────────────

class WhatsAppMessageRequest(BaseModel):
    """Payload to generate pre-filled WhatsApp message content and click-to-chat URL."""
    category: ReminderCategory = Field(..., description="Reminder category")
    member_id: UUID = Field(..., description="Target member UUID")
    membership_id: Optional[UUID] = Field(None, description="Optional membership subscription reference")
    invoice_id: Optional[UUID] = Field(None, description="Optional billing invoice reference")
    custom_message: Optional[str] = Field(None, max_length=1000, description="Optional custom override text")

    @field_validator("custom_message")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class WhatsAppMessageResponse(BaseModel):
    """Generated WhatsApp communication details."""
    category: ReminderCategory
    member_id: UUID
    member_name: str
    phone: Optional[str] = None
    clean_phone: Optional[str] = None
    message_text: str
    whatsapp_url: Optional[str] = None
    can_send: bool
    warning: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Expiry Worklist Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ExpiryItem(BaseModel):
    """Single membership record requiring expiry attention."""
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    member_email: Optional[str] = None
    member_code: Optional[str] = None
    membership_id: UUID
    plan_name: str
    start_date: date
    end_date: date
    membership_status: str
    days_until_expiry: int
    expiry_category: str  # EXPIRING_SOON, EXPIRING_TODAY, EXPIRED, LAPSED
    outstanding_balance_paise: int = 0
    last_contact_date: Optional[datetime] = None
    last_contact_outcome: Optional[str] = None
    next_follow_up_date: Optional[date] = None


class ExpiryWorklistResponse(BaseModel):
    """Paginated membership expiry worklist."""
    items: List[ExpiryItem]
    total: int
    page: int
    page_size: int
    pages: int
    expiring_soon_count: int = 0
    expiring_today_count: int = 0
    expired_count: int = 0
    lapsed_count: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Renewal Follow-up Worklist Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RenewalFollowUpItem(BaseModel):
    """Member requiring renewal outreach."""
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    member_email: Optional[str] = None
    member_code: Optional[str] = None
    membership_id: UUID
    plan_name: str
    start_date: date
    end_date: date
    membership_status: str
    outstanding_balance_paise: int = 0
    last_contact_date: Optional[datetime] = None
    last_contact_outcome: Optional[str] = None
    next_follow_up_date: Optional[date] = None
    follow_up_status: str  # OVERDUE, PENDING, NONE


class RenewalWorklistResponse(BaseModel):
    """Paginated renewal follow-up worklist."""
    items: List[RenewalFollowUpItem]
    total: int
    page: int
    page_size: int
    pages: int


# ──────────────────────────────────────────────────────────────────────────────
# Outstanding Dues Worklist Schemas
# ──────────────────────────────────────────────────────────────────────────────

class DuesWorklistItem(BaseModel):
    """Unpaid or partially paid invoice requiring payment follow-up."""
    invoice_id: UUID
    invoice_number: str
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    member_code: Optional[str] = None
    membership_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    issue_date: date
    due_date: date
    amount_paise: int
    paid_amount_paise: int
    balance_amount_paise: int
    invoice_status: str
    days_overdue: int
    ageing_category: str  # 0-7 days, 8-30 days, 30+ days
    last_contact_date: Optional[datetime] = None
    last_contact_outcome: Optional[str] = None
    next_follow_up_date: Optional[date] = None


class DuesWorklistResponse(BaseModel):
    """Paginated outstanding dues worklist with financial ageing aggregates."""
    items: List[DuesWorklistItem]
    total: int
    page: int
    page_size: int
    pages: int
    total_dues_paise: int = 0
    days_0_7_paise: int = 0
    days_8_30_paise: int = 0
    days_over_30_paise: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Birthday Reminders Schemas
# ──────────────────────────────────────────────────────────────────────────────

class BirthdayItem(BaseModel):
    """Member birthday reminder item."""
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    member_code: Optional[str] = None
    date_of_birth: date
    next_birthday: date
    days_until_birthday: int
    turning_age: Optional[int] = None
    is_today: bool
    membership_status: Optional[str] = None
    last_contact_date: Optional[datetime] = None


class BirthdayWorklistResponse(BaseModel):
    """Paginated upcoming birthdays worklist."""
    items: List[BirthdayItem]
    total: int
    page: int
    page_size: int
    pages: int
    today_birthdays_count: int = 0
    upcoming_birthdays_count: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Reminder Contact Log Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ReminderContactCreateRequest(BaseModel):
    """Payload to record an actual contact attempt or follow-up interaction."""
    member_id: UUID = Field(..., description="Target member UUID")
    category: ReminderCategory = Field(..., description="Category of communication")
    channel: ContactChannel = Field(..., description="Channel used (WHATSAPP, PHONE, IN_PERSON)")
    outcome: ContactOutcome = Field(..., description="Outcome of interaction")
    message_snippet: Optional[str] = Field(None, max_length=500, description="Snapshot of message content or template")
    notes: Optional[str] = Field(None, max_length=1000, description="Staff interaction notes")
    contact_time: Optional[datetime] = Field(None, description="UTC contact timestamp (defaults to now)")
    follow_up_date: Optional[date] = Field(None, description="Optional scheduled next follow-up date")

    @field_validator("message_snippet", "notes")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class ReminderContactResponse(BaseModel):
    """Audit record of a logged contact interaction."""
    id: UUID
    tenant_id: UUID
    member_id: UUID
    member_name: Optional[str] = None
    member_phone: Optional[str] = None
    staff_user_id: Optional[UUID] = None
    staff_user_name: Optional[str] = None
    category: ReminderCategory
    channel: ContactChannel
    outcome: ContactOutcome
    message_snippet: Optional[str] = None
    notes: Optional[str] = None
    contact_time: datetime
    follow_up_date: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReminderContactListResponse(BaseModel):
    """Paginated list of contact history records."""
    items: List[ReminderContactResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ──────────────────────────────────────────────────────────────────────────────
# Follow-up Management Schemas
# ──────────────────────────────────────────────────────────────────────────────

class FollowUpItem(BaseModel):
    """Scheduled follow-up action for a member."""
    contact_log_id: UUID
    member_id: UUID
    member_name: str
    member_phone: Optional[str] = None
    staff_user_id: Optional[UUID] = None
    staff_user_name: Optional[str] = None
    category: ReminderCategory
    last_channel: ContactChannel
    last_outcome: ContactOutcome
    last_contact_time: datetime
    follow_up_date: date
    days_overdue: int
    is_overdue: bool
    notes: Optional[str] = None


class FollowUpListResponse(BaseModel):
    """Paginated list of pending and overdue follow-up tasks."""
    items: List[FollowUpItem]
    total: int
    page: int
    page_size: int
    pages: int
    overdue_count: int = 0
    due_today_count: int = 0
    upcoming_count: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Gym Reminder & Expiry Policy Settings Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ReminderSettingsResponse(BaseModel):
    """Gym-level expiry threshold and reminder configuration."""
    tenant_id: UUID
    membership_lapsed_grace_days: int
    membership_expiry_warning_days: int

    model_config = ConfigDict(from_attributes=True)


class ReminderSettingsUpdateRequest(BaseModel):
    """Payload to update gym-level lapse grace period and expiry warning settings."""
    membership_lapsed_grace_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Grace period in days after expiration before marking subscription as lapsed",
    )
    membership_expiry_warning_days: Optional[int] = Field(
        None,
        ge=1,
        le=90,
        description="Lookahead days before expiration to mark subscription as expiring soon",
    )


