"""MembershipPlan model — configurable subscription plans scoped to a Tenant."""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UUID,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.membership import Membership


class DurationUnit(str, enum.Enum):
    """Unit of duration for a membership plan."""
    DAYS = "DAYS"
    MONTHS = "MONTHS"


class MembershipPlan(Base):
    """
    Configurable membership plan (e.g. Monthly, Quarterly, Yearly) for a Tenant gym.
    Supports monthly, quarterly, half-yearly, yearly or any custom duration.
    """
    __tablename__ = "membership_plans"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique plan UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym identifier enforcing multi-tenant isolation",
    )

    # Plan details
    name = Column(
        String(255),
        nullable=False,
        doc="Plan display name (e.g. Monthly, Quarterly, Annual Premium)",
    )
    description = Column(
        Text,
        nullable=True,
        doc="Optional description of plan features and inclusions",
    )
    duration = Column(
        Integer,
        nullable=False,
        doc="Duration quantity (used together with duration_unit)",
    )
    duration_unit = Column(
        SQLEnum(DurationUnit, name="duration_unit", native_enum=True),
        nullable=False,
        default=DurationUnit.MONTHS,
        doc="Duration unit: DAYS or MONTHS",
    )

    # Pricing (INR stored as exact decimal)
    price = Column(
        Numeric(10, 2),
        nullable=False,
        doc="Plan price in INR (Indian Rupees)",
    )

    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether this plan is currently offered to new members",
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
        back_populates="membership_plans",
        foreign_keys=[tenant_id],
        doc="Associated gym tenant",
    )
    memberships = relationship(
        "Membership",
        back_populates="membership_plan",
        foreign_keys="Membership.membership_plan_id",
        doc="Active memberships using this plan",
    )

    __table_args__ = (
        CheckConstraint("duration > 0", name="chk_membership_plans_duration_positive"),
        CheckConstraint("price >= 0", name="chk_membership_plans_price_non_negative"),
        UniqueConstraint("id", "tenant_id", name="uq_membership_plans_id_tenant"),
    )

    def __repr__(self) -> str:
        return (
            f"<MembershipPlan id={self.id} name='{self.name}' "
            f"duration={self.duration} {self.duration_unit} price={self.price}>"
        )

