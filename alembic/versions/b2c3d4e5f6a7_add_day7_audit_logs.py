"""add_day7_audit_logs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-08 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Day 7 audit_logs table and performance indexes."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column(
            "before_values",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "after_values",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"])
    op.create_index("idx_audit_logs_tenant_resource", "audit_logs", ["tenant_id", "resource_type", "resource_id"])
    op.create_index("idx_audit_logs_tenant_user", "audit_logs", ["tenant_id", "user_id"])
    op.create_index("idx_audit_logs_tenant_action", "audit_logs", ["tenant_id", "action"])


def downgrade() -> None:
    """Drop Day 7 audit_logs table and indexes."""
    op.drop_index("idx_audit_logs_tenant_action", table_name="audit_logs")
    op.drop_index("idx_audit_logs_tenant_user", table_name="audit_logs")
    op.drop_index("idx_audit_logs_tenant_resource", table_name="audit_logs")
    op.drop_index("idx_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_table("audit_logs")

