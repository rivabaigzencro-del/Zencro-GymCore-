"""Invoice model — billing invoices for memberships and gym charges strictly scoped to Tenant."""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
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
    from app.models.membership import Membership
    from app.models.payment import Payment


class InvoiceStatus(str, enum.Enum):
    """Lifecycle status of a billing invoice."""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(Base):
    """
    Billing invoice for membership fees or other gym charges.
    Scoped strictly to a Tenant and Member.
    All monetary amounts are stored in integer paise.
    """
    __tablename__ = "invoices"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique invoice UUID identifier",
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
        doc="Associated gym member being billed",
    )
    membership_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional linked membership subscription",
    )
    invoice_number = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Tenant-scoped unique invoice reference number (e.g. INV-202611-0001)",
    )
    amount_paise = Column(
        Integer,
        nullable=False,
        doc="Total invoice amount in integer paise (₹1 = 100 paise)",
    )
    paid_amount_paise = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total amount paid against this invoice in integer paise",
    )
    balance_amount_paise = Column(
        Integer,
        nullable=False,
        doc="Remaining balance owed on this invoice in integer paise",
    )
    invoice_status = Column(
        SQLEnum(InvoiceStatus, name="invoice_status", native_enum=True),
        nullable=False,
        default=InvoiceStatus.ISSUED,
        index=True,
        doc="Current lifecycle status of the invoice",
    )
    issue_date = Column(
        Date,
        nullable=False,
        doc="Date when invoice was issued",
    )
    due_date = Column(
        Date,
        nullable=False,
        doc="Date when payment is due",
    )
    description = Column(
        String(500),
        nullable=True,
        doc="Optional billing description or item summary",
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
        back_populates="invoices",
        foreign_keys=[tenant_id],
        doc="Associated gym facility tenant",
    )
    member = relationship(
        "Member",
        back_populates="invoices",
        foreign_keys=[member_id],
        doc="Associated gym member",
    )
    membership = relationship(
        "Membership",
        back_populates="invoices",
        foreign_keys=[membership_id],
        doc="Optional associated membership subscription",
    )
    payments = relationship(
        "Payment",
        back_populates="invoice",
        foreign_keys="Payment.invoice_id",
        cascade="all, delete-orphan",
        order_by="Payment.created_at.desc()",
        doc="Payments received against this invoice",
    )

    __table_args__ = (
        CheckConstraint("amount_paise >= 0", name="chk_invoices_amount_non_negative"),
        CheckConstraint("paid_amount_paise >= 0", name="chk_invoices_paid_amount_non_negative"),
        CheckConstraint("paid_amount_paise <= amount_paise", name="chk_invoices_paid_le_amount"),
        CheckConstraint("balance_amount_paise >= 0", name="chk_invoices_balance_non_negative"),
        CheckConstraint(
            "balance_amount_paise = amount_paise - paid_amount_paise",
            name="chk_invoices_balance_consistent",
        ),
        CheckConstraint("due_date >= issue_date", name="chk_invoices_due_date_valid"),
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoices_tenant_invoice_number"),
        UniqueConstraint("id", "tenant_id", name="uq_invoices_id_tenant"),
        ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="RESTRICT",
            name="fk_invoices_member_tenant",
        ),
        ForeignKeyConstraint(
            ["membership_id", "tenant_id"],
            ["memberships.id", "memberships.tenant_id"],
            ondelete="SET NULL",
            name="fk_invoices_membership_tenant",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice id={self.id} number='{self.invoice_number}' "
            f"amount={self.amount_paise} paid={self.paid_amount_paise} status={self.invoice_status}>"
        )

