"""Reminder and Contact Log model — tracks reminder interactions and follow-ups strictly scoped to Tenant."""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UUID,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.member import Member
    from app.models.user import User


class ReminderCategory(str, enum.Enum):
    """Category of the reminder or communication."""
    MEMBERSHIP_EXPIRING = "MEMBERSHIP_EXPIRING"
    MEMBERSHIP_EXPIRED = "MEMBERSHIP_EXPIRED"
    PAYMENT_DUE = "PAYMENT_DUE"
    RENEWAL_FOLLOWUP = "RENEWAL_FOLLOWUP"
    BIRTHDAY = "BIRTHDAY"


class ContactChannel(str, enum.Enum):
    """Channel through which staff reached out or attempted to reach out."""
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    IN_PERSON = "IN_PERSON"


class ContactOutcome(str, enum.Enum):
    """Outcome of the communication attempt."""
    REACHED = "REACHED"
    LEFT_MESSAGE = "LEFT_MESSAGE"
    NO_ANSWER = "NO_ANSWER"
    PROMISED_TO_PAY = "PROMISED_TO_PAY"
    RENEWED = "RENEWED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALL_BACK_REQUESTED = "CALL_BACK_REQUESTED"
    OTHER = "OTHER"


class ReminderLog(Base):
    """
    Audit log of reminder and follow-up communications with members.
    Scoped strictly to a Tenant and Member.
    Preserves historical communication records and optional next follow-up scheduling.
    """
    __tablename__ = "reminder_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique reminder contact log UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym facility identifier enforcing multi-tenant isolation",
    )
    member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated gym member contacted",
    )
    staff_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Staff member who performed the contact attempt",
    )
    category = Column(
        SQLEnum(ReminderCategory, name="reminder_category", native_enum=True),
        nullable=False,
        index=True,
        doc="Category of the reminder",
    )
    channel = Column(
        SQLEnum(ContactChannel, name="contact_channel", native_enum=True),
        nullable=False,
        doc="Communication channel used (WHATSAPP, PHONE, IN_PERSON)",
    )
    outcome = Column(
        SQLEnum(ContactOutcome, name="contact_outcome", native_enum=True),
        nullable=False,
        doc="Outcome of the contact attempt",
    )
    message_snippet = Column(
        String(500),
        nullable=True,
        doc="Snapshot or preview of the message content prepared or delivered",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Staff notes regarding the discussion or response",
    )
    contact_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="UTC timestamp when the contact attempt occurred",
    )
    follow_up_date = Column(
        Date,
        nullable=True,
        index=True,
        doc="Optional scheduled date for the next follow-up action",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        doc="UTC creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="UTC last update timestamp",
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        back_populates="reminder_logs",
        foreign_keys=[tenant_id],
        doc="Associated gym tenant",
    )
    member = relationship(
        "Member",
        back_populates="reminder_logs",
        foreign_keys=[member_id],
        doc="Associated gym member",
    )
    staff_user = relationship(
        "User",
        foreign_keys=[staff_user_id],
        doc="Staff user who logged this communication",
    )

    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_reminder_logs_id_tenant"),
        ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="CASCADE",
            name="fk_reminder_logs_member_tenant",
        ),
        Index("ix_reminder_logs_tenant_member", "tenant_id", "member_id"),
        Index("ix_reminder_logs_tenant_followup", "tenant_id", "follow_up_date"),
        Index("ix_reminder_logs_tenant_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReminderLog id={self.id} member_id={self.member_id} "
            f"category={self.category} channel={self.channel} outcome={self.outcome}>"
        )

