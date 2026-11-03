"""Receipt model — payment receipts strictly scoped to Tenant and Payment."""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    UUID,
    UniqueConstraint,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.payment import Payment


class Receipt(Base):
    """
    Payment receipt issued for a completed payment transaction.
    Scoped strictly to a Tenant and Payment.
    Receipt numbers are sequentially unique per tenant.
    Receipts are never deleted, even if a payment is subsequently refunded.
    """
    __tablename__ = "receipts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique receipt UUID identifier",
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
        unique=True,
        index=True,
        doc="Completed payment transaction this receipt is issued for",
    )
    receipt_number = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Tenant-scoped unique receipt reference number (e.g. REC-202611-0001)",
    )
    issued_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp when receipt was generated and issued",
    )
    notes = Column(
        String(500),
        nullable=True,
        doc="Optional receipt notes or disclaimer comments",
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
        back_populates="receipts",
        foreign_keys=[tenant_id],
        doc="Associated gym facility tenant",
    )
    payment = relationship(
        "Payment",
        back_populates="receipt",
        foreign_keys=[payment_id],
        doc="Associated payment transaction",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "receipt_number", name="uq_receipts_tenant_receipt_number"),
        UniqueConstraint("payment_id", name="uq_receipts_payment_id"),
        UniqueConstraint("id", "tenant_id", name="uq_receipts_id_tenant"),
        ForeignKeyConstraint(
            ["payment_id", "tenant_id"],
            ["payments.id", "payments.tenant_id"],
            ondelete="RESTRICT",
            name="fk_receipts_payment_tenant",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Receipt id={self.id} number='{self.receipt_number}' "
            f"payment_id={self.payment_id} tenant_id={self.tenant_id}>"
        )

