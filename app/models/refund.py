"""Refund model — audit trail of refunds and reversals strictly scoped to Tenant and Payment."""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UUID,
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.payment import Payment
    from app.models.user import User


class RefundType(str, enum.Enum):
    """Classification of the returned funds."""
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"


class RefundStatus(str, enum.Enum):
    """Status of the refund or reversal transaction."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Refund(Base):
    """
    Audit record for refunds and payment reversals.
    Scoped strictly to a Tenant and Payment.
    Never deletes the original payment record.
    All monetary amounts are stored in integer paise.
    """
    __tablename__ = "refunds"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique refund UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym facility identifier enforcing multi-tenant isolation",
    )
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Payment transaction against which refund or reversal is recorded",
    )
    amount_paise = Column(
        Integer,
        nullable=False,
        doc="Refund/reversal amount in integer paise (₹1 = 100 paise)",
    )
    reason = Column(
        String(500),
        nullable=False,
        doc="Reason for refund or reversal (audit requirement)",
    )
    refund_type = Column(
        SQLEnum(RefundType, name="refund_type", native_enum=True),
        nullable=False,
        default=RefundType.REFUND,
        doc="Type of transaction (REFUND or REVERSAL)",
    )
    status = Column(
        SQLEnum(RefundStatus, name="refund_status", native_enum=True),
        nullable=False,
        default=RefundStatus.COMPLETED,
        index=True,
        doc="Processing status of the refund/reversal",
    )
    transaction_reference = Column(
        String(100),
        nullable=True,
        doc="External reference or payout transaction ID",
    )
    initiated_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Staff user who initiated the refund or reversal",
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
        back_populates="refunds",
        foreign_keys=[tenant_id],
        doc="Associated gym facility tenant",
    )
    payment = relationship(
        "Payment",
        back_populates="refunds",
        foreign_keys=[payment_id],
        doc="Associated payment transaction",
    )
    initiated_by = relationship(
        "User",
        foreign_keys=[initiated_by_id],
        doc="Staff member who processed the refund/reversal",
    )

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_refunds_amount_positive"),
        UniqueConstraint("id", "tenant_id", name="uq_refunds_id_tenant"),
        ForeignKeyConstraint(
            ["payment_id", "tenant_id"],
            ["payments.id", "payments.tenant_id"],
            ondelete="RESTRICT",
            name="fk_refunds_payment_tenant",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Refund id={self.id} payment_id={self.payment_id} "
            f"amount={self.amount_paise} type={self.refund_type} status={self.status}>"
        )

