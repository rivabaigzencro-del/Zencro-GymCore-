"""Payment model — payment transaction records strictly scoped to Tenant."""
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
    from app.models.member import Member
    from app.models.invoice import Invoice
    from app.models.receipt import Receipt
    from app.models.refund import Refund


class PaymentMethod(str, enum.Enum):
    """Supported payment methods for gym fee collections."""
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"


class PaymentStatus(str, enum.Enum):
    """Lifecycle status of a payment transaction."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    REVERSED = "REVERSED"


class Payment(Base):
    """
    Payment transaction record for gym membership fees and other billings.
    Scoped strictly to a Tenant and Member.
    Supports partial payments against invoices, receipt generation, and refunds.
    All monetary amounts are stored in integer paise.
    """
    __tablename__ = "payments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique payment UUID identifier",
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
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Associated gym member making the payment",
    )
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional billing invoice this payment applies against",
    )
    amount_paise = Column(
        Integer,
        nullable=False,
        doc="Payment amount in integer paise (₹1 = 100 paise)",
    )
    payment_method = Column(
        SQLEnum(PaymentMethod, name="payment_method", native_enum=True),
        nullable=False,
        index=True,
        doc="Method used for payment (CASH, UPI, CARD, BANK_TRANSFER, CHEQUE)",
    )
    payment_status = Column(
        SQLEnum(PaymentStatus, name="payment_status", native_enum=True),
        nullable=False,
        default=PaymentStatus.COMPLETED,
        index=True,
        doc="Status of the payment transaction",
    )
    transaction_reference = Column(
        String(100),
        nullable=True,
        doc="External reference identifier (e.g. UPI txn ID, cheque number, bank ref)",
    )
    payment_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp when the payment occurred",
    )
    notes = Column(
        String(500),
        nullable=True,
        doc="Staff notes or comments regarding this transaction",
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
        back_populates="payments",
        foreign_keys=[tenant_id],
        doc="Associated gym facility tenant",
    )
    member = relationship(
        "Member",
        back_populates="payments",
        foreign_keys=[member_id],
        doc="Associated gym member",
    )
    invoice = relationship(
        "Invoice",
        back_populates="payments",
        foreign_keys=[invoice_id],
        doc="Optional associated billing invoice",
    )
    receipt = relationship(
        "Receipt",
        back_populates="payment",
        uselist=False,
        foreign_keys="Receipt.payment_id",
        cascade="all, delete-orphan",
        doc="Generated payment receipt",
    )
    refunds = relationship(
        "Refund",
        back_populates="payment",
        foreign_keys="Refund.payment_id",
        cascade="all, delete-orphan",
        order_by="Refund.created_at.desc()",
        doc="Refund and reversal records against this payment",
    )

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_payments_amount_positive"),
        UniqueConstraint("id", "tenant_id", name="uq_payments_id_tenant"),
        ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="RESTRICT",
            name="fk_payments_member_tenant",
        ),
        ForeignKeyConstraint(
            ["invoice_id", "tenant_id"],
            ["invoices.id", "invoices.tenant_id"],
            ondelete="SET NULL",
            name="fk_payments_invoice_tenant",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} amount={self.amount_paise} method={self.payment_method} "
            f"status={self.payment_status} tenant_id={self.tenant_id}>"
        )

