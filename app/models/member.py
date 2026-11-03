"""Member model — gym member scoped strictly to a Tenant."""
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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.membership import Membership
    from app.models.invoice import Invoice
    from app.models.payment import Payment
    from app.models.attendance import Attendance


class MemberStatus(str, enum.Enum):
    """Lifecycle status of a gym member account."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class Gender(str, enum.Enum):
    """Member gender options."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class Member(Base):
    """
    Gym member entity strictly scoped to a Tenant.
    Prevents duplicate members within the same gym via tenant-scoped unique
    constraints on phone and email when provided.
    """
    __tablename__ = "members"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique member UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym identifier enforcing multi-tenant isolation",
    )

    # Personal information
    full_name = Column(
        String(255),
        nullable=False,
        doc="Full name of the gym member",
    )
    email = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Member email address (optional but unique within tenant when provided)",
    )
    phone = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Primary contact phone number",
    )
    gender = Column(
        SQLEnum(Gender, name="gender", native_enum=True),
        nullable=True,
        doc="Member gender",
    )
    date_of_birth = Column(
        Date,
        nullable=True,
        doc="Member date of birth",
    )
    address = Column(
        Text,
        nullable=True,
        doc="Member residential address",
    )

    # Emergency contact
    emergency_contact_name = Column(
        String(255),
        nullable=True,
        doc="Name of emergency contact person",
    )
    emergency_contact_phone = Column(
        String(50),
        nullable=True,
        doc="Phone number of emergency contact person",
    )

    # Status
    status = Column(
        SQLEnum(MemberStatus, name="member_status", native_enum=True),
        nullable=False,
        default=MemberStatus.ACTIVE,
        doc="Current lifecycle status of the member",
    )

    # Identifiers for Attendance and Check-in
    member_code = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Human-readable member code or barcode (e.g. MEM-0001)",
    )
    qr_code = Column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
        doc="Secure opaque random identifier for QR attendance check-in",
    )

    # Timestamps
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
        back_populates="members",
        foreign_keys=[tenant_id],
        doc="Associated gym tenant",
    )
    memberships = relationship(
        "Membership",
        back_populates="member",
        foreign_keys="Membership.member_id",
        cascade="all, delete-orphan",
        order_by="Membership.created_at.desc()",
        doc="Membership records for this member",
    )
    invoices = relationship(
        "Invoice",
        back_populates="member",
        foreign_keys="Invoice.member_id",
        cascade="all, delete-orphan",
        order_by="Invoice.created_at.desc()",
        doc="Billing invoices issued for this member",
    )
    payments = relationship(
        "Payment",
        back_populates="member",
        foreign_keys="Payment.member_id",
        cascade="all, delete-orphan",
        order_by="Payment.created_at.desc()",
        doc="Payments made by this member",
    )
    attendance_records = relationship(
        "Attendance",
        back_populates="member",
        foreign_keys="Attendance.member_id",
        cascade="all, delete-orphan",
        order_by="Attendance.check_in_time.desc()",
        doc="Attendance records for this member",
    )
    reminder_logs = relationship(
        "ReminderLog",
        back_populates="member",
        foreign_keys="ReminderLog.member_id",
        cascade="all, delete-orphan",
        order_by="ReminderLog.contact_time.desc()",
        doc="Reminder and follow-up contact logs for this member",
    )

    __table_args__ = (
        # A member's phone must be unique within a tenant when provided
        UniqueConstraint("tenant_id", "phone", name="uq_members_tenant_phone"),
        # Email unique within tenant when provided
        UniqueConstraint("tenant_id", "email", name="uq_members_tenant_email"),
        # Member code unique within tenant when provided
        UniqueConstraint("tenant_id", "member_code", name="uq_members_tenant_member_code"),
        # Composite unique identifier supporting composite foreign keys from memberships
        UniqueConstraint("id", "tenant_id", name="uq_members_id_tenant"),
    )

    def __repr__(self) -> str:
        return f"<Member id={self.id} name='{self.full_name}' tenant_id={self.tenant_id}>"

