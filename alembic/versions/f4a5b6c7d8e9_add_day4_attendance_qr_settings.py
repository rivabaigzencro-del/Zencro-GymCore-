"""add_day4_attendance_qr_settings

Revision ID: f4a5b6c7d8e9
Revises: e3f6a7b8c9d0
Create Date: 2026-11-03 13:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Day 4 attendance tables, check-in enum, member QR/code columns, and gym settings."""
    # 1. Add attendance settings to tenants
    op.add_column("tenants", sa.Column("attendance_block_expired", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("tenants", sa.Column("attendance_allow_override", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("tenants", sa.Column("attendance_block_on_dues", sa.Boolean(), server_default="false", nullable=False))

    # 2. Add member_code and qr_code to members
    op.add_column("members", sa.Column("member_code", sa.String(length=50), nullable=True))
    op.add_column("members", sa.Column("qr_code", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_members_member_code"), "members", ["member_code"], unique=False)
    op.create_index(op.f("ix_members_qr_code"), "members", ["qr_code"], unique=True)
    op.create_unique_constraint("uq_members_tenant_member_code", "members", ["tenant_id", "member_code"])

    # 3. Create attendance table
    op.create_table(
        "attendance",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("member_id", sa.UUID(), nullable=False),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "check_in_method",
            sa.Enum("MANUAL", "QR", name="check_in_method"),
            server_default="MANUAL",
            nullable=False,
        ),
        sa.Column("checked_in_by_id", sa.UUID(), nullable=True),
        sa.Column("checked_out_by_id", sa.UUID(), nullable=True),
        sa.Column("is_override", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("override_reason", sa.String(length=500), nullable=True),
        sa.Column("override_by_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checked_in_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checked_out_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["override_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="CASCADE",
            name="fk_attendance_member_tenant",
        ),
        sa.CheckConstraint(
            "(check_out_time IS NULL) OR (check_out_time >= check_in_time)",
            name="chk_attendance_checkout_after_checkin",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_attendance_id_tenant"),
    )
    op.create_index(op.f("ix_attendance_id"), "attendance", ["id"], unique=False)
    op.create_index(op.f("ix_attendance_tenant_id"), "attendance", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_attendance_member_id"), "attendance", ["member_id"], unique=False)
    op.create_index(op.f("ix_attendance_check_in_time"), "attendance", ["check_in_time"], unique=False)
    op.create_index(op.f("ix_attendance_check_out_time"), "attendance", ["check_out_time"], unique=False)
    op.create_index(op.f("ix_attendance_checked_in_by_id"), "attendance", ["checked_in_by_id"], unique=False)
    op.create_index(op.f("ix_attendance_checked_out_by_id"), "attendance", ["checked_out_by_id"], unique=False)
    op.create_index(op.f("ix_attendance_override_by_id"), "attendance", ["override_by_id"], unique=False)
    op.create_index(
        "ix_attendance_active_member",
        "attendance",
        ["member_id"],
        unique=True,
        postgresql_where=sa.text("check_out_time IS NULL"),
    )


def downgrade() -> None:
    """Drop Day 4 attendance tables, constraints, enums, and member/tenant columns in reverse order."""
    op.drop_table("attendance")

    op.execute("DROP TYPE IF EXISTS check_in_method")

    op.drop_constraint("uq_members_tenant_member_code", "members", type_="unique")
    op.drop_index(op.f("ix_members_qr_code"), table_name="members")
    op.drop_index(op.f("ix_members_member_code"), table_name="members")
    op.drop_column("members", "qr_code")
    op.drop_column("members", "member_code")

    op.drop_column("tenants", "attendance_block_on_dues")
    op.drop_column("tenants", "attendance_allow_override")
    op.drop_column("tenants", "attendance_block_expired")
