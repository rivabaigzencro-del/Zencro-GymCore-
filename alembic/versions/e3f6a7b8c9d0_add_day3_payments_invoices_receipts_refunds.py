"""add_day3_payments_invoices_receipts_refunds

Revision ID: e3f6a7b8c9d0
Revises: d2e5a6f7b8c9
Create Date: 2026-11-03 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e3f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d2e5a6f7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Day 3 financial tables, enums, constraints, and composite foreign keys."""
    # 0. Add composite unique constraint on memberships to support composite FK from invoices
    op.create_unique_constraint(
        "uq_memberships_id_tenant",
        "memberships",
        ["id", "tenant_id"],
    )

    # 1. Invoices table
    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("member_id", sa.UUID(), nullable=False),
        sa.Column("membership_id", sa.UUID(), nullable=True),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("paid_amount_paise", sa.Integer(), server_default="0", nullable=False),
        sa.Column("balance_amount_paise", sa.Integer(), nullable=False),
        sa.Column(
            "invoice_status",
            sa.Enum("DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED", name="invoice_status"),
            server_default="ISSUED",
            nullable=False,
        ),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="RESTRICT",
            name="fk_invoices_member_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id", "tenant_id"],
            ["memberships.id", "memberships.tenant_id"],
            ondelete="SET NULL",
            name="fk_invoices_membership_tenant",
        ),
        sa.CheckConstraint("amount_paise >= 0", name="chk_invoices_amount_non_negative"),
        sa.CheckConstraint("paid_amount_paise >= 0", name="chk_invoices_paid_amount_non_negative"),
        sa.CheckConstraint("paid_amount_paise <= amount_paise", name="chk_invoices_paid_le_amount"),
        sa.CheckConstraint("balance_amount_paise >= 0", name="chk_invoices_balance_non_negative"),
        sa.CheckConstraint("balance_amount_paise = amount_paise - paid_amount_paise", name="chk_invoices_balance_consistent"),
        sa.CheckConstraint("due_date >= issue_date", name="chk_invoices_due_date_valid"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_invoices_id_tenant"),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_invoices_tenant_invoice_number"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)
    op.create_index(op.f("ix_invoices_tenant_id"), "invoices", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_invoices_member_id"), "invoices", ["member_id"], unique=False)
    op.create_index(op.f("ix_invoices_membership_id"), "invoices", ["membership_id"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_status"), "invoices", ["invoice_status"], unique=False)

    # 3. Payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("member_id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("CASH", "UPI", "CARD", "BANK_TRANSFER", "CHEQUE", name="payment_method"),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum("PENDING", "COMPLETED", "FAILED", "PARTIALLY_REFUNDED", "REFUNDED", "REVERSED", name="payment_status"),
            server_default="COMPLETED",
            nullable=False,
        ),
        sa.Column("transaction_reference", sa.String(length=100), nullable=True),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="RESTRICT",
            name="fk_payments_member_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id", "tenant_id"],
            ["invoices.id", "invoices.tenant_id"],
            ondelete="SET NULL",
            name="fk_payments_invoice_tenant",
        ),
        sa.CheckConstraint("amount_paise > 0", name="chk_payments_amount_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_payments_id_tenant"),
    )
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_payments_member_id"), "payments", ["member_id"], unique=False)
    op.create_index(op.f("ix_payments_invoice_id"), "payments", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_payments_payment_method"), "payments", ["payment_method"], unique=False)
    op.create_index(op.f("ix_payments_payment_status"), "payments", ["payment_status"], unique=False)

    # 4. Receipts table
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("receipt_number", sa.String(length=50), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["payment_id", "tenant_id"],
            ["payments.id", "payments.tenant_id"],
            ondelete="RESTRICT",
            name="fk_receipts_payment_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_receipts_id_tenant"),
        sa.UniqueConstraint("payment_id", name="uq_receipts_payment_id"),
        sa.UniqueConstraint("tenant_id", "receipt_number", name="uq_receipts_tenant_receipt_number"),
    )
    op.create_index(op.f("ix_receipts_id"), "receipts", ["id"], unique=False)
    op.create_index(op.f("ix_receipts_tenant_id"), "receipts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_receipts_payment_id"), "receipts", ["payment_id"], unique=True)
    op.create_index(op.f("ix_receipts_receipt_number"), "receipts", ["receipt_number"], unique=False)

    # 5. Refunds table
    op.create_table(
        "refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "refund_type",
            sa.Enum("REFUND", "REVERSAL", name="refund_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PENDING", "COMPLETED", "FAILED", name="refund_status"),
            server_default="COMPLETED",
            nullable=False,
        ),
        sa.Column("transaction_reference", sa.String(length=100), nullable=True),
        sa.Column("initiated_by_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["payment_id", "tenant_id"],
            ["payments.id", "payments.tenant_id"],
            ondelete="RESTRICT",
            name="fk_refunds_payment_tenant",
        ),
        sa.CheckConstraint("amount_paise > 0", name="chk_refunds_amount_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_refunds_id_tenant"),
    )
    op.create_index(op.f("ix_refunds_id"), "refunds", ["id"], unique=False)
    op.create_index(op.f("ix_refunds_tenant_id"), "refunds", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_refunds_payment_id"), "refunds", ["payment_id"], unique=False)
    op.create_index(op.f("ix_refunds_initiated_by_id"), "refunds", ["initiated_by_id"], unique=False)
    op.create_index(op.f("ix_refunds_status"), "refunds", ["status"], unique=False)


def downgrade() -> None:
    """Drop Day 3 tables, constraints, composite FKs, and enums in reverse order."""
    op.drop_table("refunds")
    op.drop_table("receipts")
    op.drop_table("payments")
    op.drop_table("invoices")

    op.drop_constraint("uq_memberships_id_tenant", "memberships", type_="unique")

    op.execute("DROP TYPE IF EXISTS refund_status")
    op.execute("DROP TYPE IF EXISTS refund_type")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS invoice_status")
