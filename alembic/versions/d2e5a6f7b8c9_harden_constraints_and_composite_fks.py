"""harden_constraints_and_composite_fks

Revision ID: d2e5a6f7b8c9
Revises: c1b2e48e4ffb
Create Date: 2026-11-01 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e5a6f7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1b2e48e4ffb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database-level integrity constraints, check constraints, and composite tenant foreign keys."""
    # 1. Global user email uniqueness
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # 2. Member tenant-scoped email uniqueness and composite key for FKs
    op.create_unique_constraint("uq_members_tenant_email", "members", ["tenant_id", "email"])
    op.create_unique_constraint("uq_members_id_tenant", "members", ["id", "tenant_id"])

    # 3. MembershipPlan check constraints and composite key
    op.create_unique_constraint("uq_membership_plans_id_tenant", "membership_plans", ["id", "tenant_id"])
    op.create_check_constraint(
        "chk_membership_plans_duration_positive",
        "membership_plans",
        "duration > 0",
    )
    op.create_check_constraint(
        "chk_membership_plans_price_non_negative",
        "membership_plans",
        "price >= 0",
    )

    # 4. Membership check constraints and cross-tenant composite foreign keys
    op.create_check_constraint(
        "chk_memberships_dates_valid",
        "memberships",
        "end_date >= start_date",
    )
    op.create_check_constraint(
        "chk_memberships_frozen_days_non_negative",
        "memberships",
        "total_frozen_days >= 0",
    )
    op.create_check_constraint(
        "chk_memberships_freeze_dates_valid",
        "memberships",
        "(freeze_start_date IS NULL AND freeze_end_date IS NULL) OR "
        "(freeze_start_date IS NOT NULL AND freeze_end_date IS NOT NULL AND freeze_end_date > freeze_start_date)",
    )
    op.create_foreign_key(
        "fk_memberships_member_tenant",
        "memberships",
        "members",
        ["member_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_memberships_plan_tenant",
        "memberships",
        "membership_plans",
        ["membership_plan_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Safely remove constraints in reverse order."""
    op.drop_constraint("fk_memberships_plan_tenant", "memberships", type_="foreignkey")
    op.drop_constraint("fk_memberships_member_tenant", "memberships", type_="foreignkey")
    op.drop_constraint("chk_memberships_freeze_dates_valid", "memberships", type_="check")
    op.drop_constraint("chk_memberships_frozen_days_non_negative", "memberships", type_="check")
    op.drop_constraint("chk_memberships_dates_valid", "memberships", type_="check")

    op.drop_constraint("chk_membership_plans_price_non_negative", "membership_plans", type_="check")
    op.drop_constraint("chk_membership_plans_duration_positive", "membership_plans", type_="check")
    op.drop_constraint("uq_membership_plans_id_tenant", "membership_plans", type_="unique")

    op.drop_constraint("uq_members_id_tenant", "members", type_="unique")
    op.drop_constraint("uq_members_tenant_email", "members", type_="unique")

    op.drop_constraint("uq_users_email", "users", type_="unique")

