import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import Column, String, Text, DateTime, UUID, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.member import Member
    from app.models.membership_plan import MembershipPlan
    from app.models.membership import Membership
    from app.models.invoice import Invoice
    from app.models.payment import Payment
    from app.models.receipt import Receipt
    from app.models.refund import Refund
    from app.models.attendance import Attendance
    from app.models.audit_log import AuditLog


class Tenant(Base):
    """
    Tenant (Gym / Fitness Facility) multi-tenant root entity.
    All tenant-scoped business entities must reference tenant_id.
    """
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique tenant UUID identifier",
    )
    name = Column(
        String(255),
        nullable=False,
        doc="Name of the gym or fitness facility",
    )
    email = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Official contact email for the facility",
    )
    phone = Column(
        String(50),
        nullable=True,
        doc="Official contact phone number",
    )
    address = Column(
        Text,
        nullable=True,
        doc="Physical facility address",
    )
    timezone = Column(
        String(50),
        nullable=False,
        default="Asia/Kolkata",
        doc="Business timezone (defaults to IST / Asia/Kolkata)",
    )
    currency = Column(
        String(10),
        nullable=False,
        default="INR",
        doc="Default operating currency (defaults to INR)",
    )

    # Attendance & Check-in Policies
    attendance_block_expired = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Block check-in for expired memberships unless authorized override provided",
    )
    attendance_allow_override = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Allow staff override with mandatory audit reason for blocked check-ins",
    )
    attendance_block_on_dues = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Block check-in if member has overdue invoices",
    )

    # Expiry & Reminder Policies
    membership_lapsed_grace_days = Column(
        Integer,
        nullable=False,
        default=30,
        doc="Grace period in days after membership expiration before subscription is marked as lapsed",
    )
    membership_expiry_warning_days = Column(
        Integer,
        nullable=False,
        default=7,
        doc="Lookahead threshold in days before membership expiration to mark subscription as expiring soon",
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
    users = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="Staff/User accounts belonging to this gym tenant",
    )
    members = relationship(
        "Member",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="Gym member records belonging to this tenant",
    )
    membership_plans = relationship(
        "MembershipPlan",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="Membership plans configured by this tenant",
    )
    memberships = relationship(
        "Membership",
        back_populates="tenant",
        foreign_keys="Membership.tenant_id",
        cascade="all, delete-orphan",
        doc="All membership subscriptions for this tenant",
    )
    invoices = relationship(
        "Invoice",
        back_populates="tenant",
        foreign_keys="Invoice.tenant_id",
        cascade="all, delete-orphan",
        doc="All billing invoices for this tenant",
    )
    payments = relationship(
        "Payment",
        back_populates="tenant",
        foreign_keys="Payment.tenant_id",
        cascade="all, delete-orphan",
        doc="All payment transactions for this tenant",
    )
    receipts = relationship(
        "Receipt",
        back_populates="tenant",
        foreign_keys="Receipt.tenant_id",
        cascade="all, delete-orphan",
        doc="All payment receipts for this tenant",
    )
    refunds = relationship(
        "Refund",
        back_populates="tenant",
        foreign_keys="Refund.tenant_id",
        cascade="all, delete-orphan",
        doc="All refund and reversal records for this tenant",
    )
    attendance_records = relationship(
        "Attendance",
        back_populates="tenant",
        foreign_keys="Attendance.tenant_id",
        cascade="all, delete-orphan",
        doc="All attendance check-in records for this tenant",
    )
    reminder_logs = relationship(
        "ReminderLog",
        back_populates="tenant",
        foreign_keys="ReminderLog.tenant_id",
        cascade="all, delete-orphan",
        doc="All reminder and follow-up contact logs for this tenant",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="tenant",
        foreign_keys="AuditLog.tenant_id",
        cascade="all, delete-orphan",
        doc="All audit log entries for this tenant",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name='{self.name}'>"
