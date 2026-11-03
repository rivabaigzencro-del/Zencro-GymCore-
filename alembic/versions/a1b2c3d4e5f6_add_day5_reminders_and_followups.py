"""add_day5_reminders_and_followups

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-11-03 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Day 5 reminder_logs table, enums, indexes, and tenant reminder settings."""
    # 1. Add reminder policies to tenants
    op.add_column("tenants", sa.Column("membership_lapsed_grace_days", sa.Integer(), server_default="30", nullable=False))
    op.add_column("tenants", sa.Column("membership_expiry_warning_days", sa.Integer(), server_default="7", nullable=False))

    # 2. Create reminder_logs table
    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("member_id", sa.UUID(), nullable=False),
        sa.Column("staff_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "MEMBERSHIP_EXPIRING",
                "MEMBERSHIP_EXPIRED",
                "PAYMENT_DUE",
                "RENEWAL_FOLLOWUP",
                "BIRTHDAY",
                name="reminder_category",
            ),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum("WHATSAPP", "PHONE", "IN_PERSON", name="contact_channel"),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "REACHED",
                "LEFT_MESSAGE",
                "NO_ANSWER",
                "PROMISED_TO_PAY",
                "RENEWED",
                "NOT_INTERESTED",
                "CALL_BACK_REQUESTED",
                "OTHER",
                name="contact_outcome",
            ),
            nullable=False,
        ),
        sa.Column("message_snippet", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contact_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="CASCADE",
            name="fk_reminder_logs_member_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_reminder_logs_id_tenant"),
    )

    op.create_index(op.f("ix_reminder_logs_id"), "reminder_logs", ["id"], unique=False)
    op.create_index(op.f("ix_reminder_logs_tenant_id"), "reminder_logs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_reminder_logs_member_id"), "reminder_logs", ["member_id"], unique=False)
    op.create_index(op.f("ix_reminder_logs_staff_user_id"), "reminder_logs", ["staff_user_id"], unique=False)
    op.create_index(op.f("ix_reminder_logs_category"), "reminder_logs", ["category"], unique=False)
    op.create_index(op.f("ix_reminder_logs_contact_time"), "reminder_logs", ["contact_time"], unique=False)
    op.create_index(op.f("ix_reminder_logs_follow_up_date"), "reminder_logs", ["follow_up_date"], unique=False)
    op.create_index("ix_reminder_logs_tenant_member", "reminder_logs", ["tenant_id", "member_id"], unique=False)
    op.create_index("ix_reminder_logs_tenant_followup", "reminder_logs", ["tenant_id", "follow_up_date"], unique=False)
    op.create_index("ix_reminder_logs_tenant_category", "reminder_logs", ["tenant_id", "category"], unique=False)


def downgrade() -> None:
    """Drop Day 5 reminder_logs table, enums, and tenant columns in reverse order."""
    op.drop_table("reminder_logs")
    op.execute("DROP TYPE IF EXISTS contact_outcome")
    op.execute("DROP TYPE IF EXISTS contact_channel")
    op.execute("DROP TYPE IF EXISTS reminder_category")
    op.drop_column("tenants", "membership_expiry_warning_days")
    op.drop_column("tenants", "membership_lapsed_grace_days")

