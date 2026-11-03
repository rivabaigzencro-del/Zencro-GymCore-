"""Membership model — links a Member to a MembershipPlan with lifecycle management."""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UUID,
    String,
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.member import Member
    from app.models.membership_plan import MembershipPlan
    from app.models.invoice import Invoice


class MembershipStatus(str, enum.Enum):
    """Lifecycle status of an individual membership subscription."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FROZEN = "FROZEN"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"


class Membership(Base):
    """
    Membership subscription record linking a Member to a MembershipPlan.
    Tracks full lifecycle: active, expired, frozen and cancelled states.
    Freeze/unfreeze extends the end_date by the number of frozen days.
    """
    __tablename__ = "memberships"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique membership UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym identifier enforcing multi-tenant isolation",
    )
    member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated gym member",
    )
    membership_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("membership_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Membership plan chosen for this subscription",
    )

    # Date range
    start_date = Column(
        Date,
        nullable=False,
        doc="Subscription start date",
    )
    end_date = Column(
        Date,
        nullable=False,
        doc="Subscription end date (extended when frozen days are recovered)",
    )

    # Status
    status = Column(
        SQLEnum(MembershipStatus, name="membership_status", native_enum=True),
        nullable=False,
        default=MembershipStatus.ACTIVE,
        doc="Current lifecycle status of the membership",
    )

    # Freeze management
    freeze_start_date = Column(
        Date,
        nullable=True,
        doc="Date when the current freeze period began (null when not frozen)",
    )
    freeze_end_date = Column(
        Date,
        nullable=True,
        doc="Date when the current freeze period ends",
    )
    total_frozen_days = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total accumulated frozen days across all freeze periods",
    )

    # Renewal tracking
    renewed_from_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to the previous membership this was renewed from",
    )
    notes = Column(
        String(500),
        nullable=True,
        doc="Optional notes (e.g. upgrade reason, staff comments)",
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
        back_populates="memberships",
        foreign_keys=[tenant_id],
        doc="Associated gym tenant",
    )
    member = relationship(
        "Member",
        back_populates="memberships",
        foreign_keys=[member_id],
        doc="Associated gym member",
    )
    membership_plan = relationship(
        "MembershipPlan",
        back_populates="memberships",
        foreign_keys=[membership_plan_id],
        doc="Membership plan selected for this subscription",
    )
    renewed_from = relationship(
        "Membership",
        remote_side="Membership.id",
        foreign_keys=[renewed_from_id],
        doc="Previous membership this was renewed/upgraded from",
    )
    invoices = relationship(
        "Invoice",
        back_populates="membership",
        foreign_keys="Invoice.membership_id",
        doc="Billing invoices associated with this membership",
    )

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_memberships_dates_valid"),
        CheckConstraint("total_frozen_days >= 0", name="chk_memberships_frozen_days_non_negative"),
        CheckConstraint(
            "(freeze_start_date IS NULL AND freeze_end_date IS NULL) OR "
            "(freeze_start_date IS NOT NULL AND freeze_end_date IS NOT NULL AND freeze_end_date > freeze_start_date)",
            name="chk_memberships_freeze_dates_valid",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_memberships_id_tenant"),
        ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="CASCADE",
            name="fk_memberships_member_tenant",
        ),
        ForeignKeyConstraint(
            ["membership_plan_id", "tenant_id"],
            ["membership_plans.id", "membership_plans.tenant_id"],
            ondelete="RESTRICT",
            name="fk_memberships_plan_tenant",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Membership id={self.id} member_id={self.member_id} "
            f"status={self.status} {self.start_date}→{self.end_date}>"
        )

