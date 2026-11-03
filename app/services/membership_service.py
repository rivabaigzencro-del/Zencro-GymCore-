"""Membership service — business logic for membership lifecycle management."""
import math
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.tenant import Tenant
from app.models.member import Member, MemberStatus
from app.models.membership import Membership, MembershipStatus
from app.models.membership_plan import MembershipPlan, DurationUnit
from app.models.user import User
from app.schemas.memberships import (
    MembershipCreateRequest,
    MembershipFreezeRequest,
    MembershipRenewRequest,
    MembershipUpgradeRequest,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_gym_today(db: Optional[Session] = None, tenant_id: Optional[uuid.UUID] = None) -> date:
    """
    Return today's date in the tenant's configured timezone,
    defaulting to Indian Standard Time (IST, Asia/Kolkata).
    """
    tz_name = "Asia/Kolkata"
    if db is not None and tenant_id is not None:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.timezone:
            tz_name = tenant.timezone
    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return date.today()


def _calculate_end_date(start: date, plan: MembershipPlan) -> date:
    """Calculate membership end date from start date and plan duration."""
    if plan.duration_unit == DurationUnit.MONTHS:
        return start + relativedelta(months=plan.duration) - timedelta(days=1)
    else:  # DAYS
        return start + timedelta(days=plan.duration) - timedelta(days=1)


def _get_plan_or_404(db: Session, plan_id: uuid.UUID, tenant_id: uuid.UUID) -> MembershipPlan:
    plan = (
        db.query(MembershipPlan)
        .filter(MembershipPlan.id == plan_id, MembershipPlan.tenant_id == tenant_id)
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership plan not found",
        )
    return plan


def sync_expired_memberships(db: Session, tenant_id: uuid.UUID) -> int:
    """
    Synchronize memberships whose end_date is in the past from ACTIVE to EXPIRED.
    Also updates member statuses where appropriate to maintain consistency.
    """
    today = get_gym_today(db, tenant_id)
    expired_memberships = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date < today,
        )
        .all()
    )
    if not expired_memberships:
        return 0

    count = 0
    for ms in expired_memberships:
        ms.status = MembershipStatus.EXPIRED
        count += 1
        # If member is currently ACTIVE and has no other ACTIVE/FROZEN membership, set to EXPIRED
        has_other_active = (
            db.query(Membership)
            .filter(
                Membership.member_id == ms.member_id,
                Membership.tenant_id == tenant_id,
                Membership.id != ms.id,
                Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.FROZEN]),
            )
            .first()
        )
        if not has_other_active:
            member = (
                db.query(Member)
                .filter(Member.id == ms.member_id, Member.tenant_id == tenant_id)
                .first()
            )
            if member and member.status == MemberStatus.ACTIVE:
                member.status = MemberStatus.EXPIRED

    if count > 0:
        db.commit()
    return count


def _get_membership_or_404(
    db: Session, membership_id: uuid.UUID, tenant_id: uuid.UUID
) -> Membership:
    membership = (
        db.query(Membership)
        .options(joinedload(Membership.member), joinedload(Membership.membership_plan))
        .filter(Membership.id == membership_id, Membership.tenant_id == tenant_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    # Check if active membership has reached or passed expiry
    today = get_gym_today(db, tenant_id)
    if membership.status == MembershipStatus.ACTIVE and membership.end_date < today:
        membership.status = MembershipStatus.EXPIRED
        has_other_active = (
            db.query(Membership)
            .filter(
                Membership.member_id == membership.member_id,
                Membership.tenant_id == tenant_id,
                Membership.id != membership.id,
                Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.FROZEN]),
            )
            .first()
        )
        if not has_other_active:
            member = (
                db.query(Member)
                .filter(Member.id == membership.member_id, Member.tenant_id == tenant_id)
                .first()
            )
            if member and member.status == MemberStatus.ACTIVE:
                member.status = MemberStatus.EXPIRED
        db.commit()
        db.refresh(membership)
    return membership


# ──────────────────────────────────────────────────────────────────────────────
# Membership Plan CRUD
# ──────────────────────────────────────────────────────────────────────────────

def create_membership_plan(db: Session, payload, current_user: User) -> MembershipPlan:
    """Create a new membership plan for the tenant."""
    plan = MembershipPlan(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=payload.name,
        description=payload.description,
        duration=payload.duration,
        duration_unit=payload.duration_unit,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_membership_plans(
    db: Session,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
) -> dict:
    """List membership plans for the tenant."""
    query = db.query(MembershipPlan).filter(MembershipPlan.tenant_id == tenant_id)
    if not include_inactive:
        query = query.filter(MembershipPlan.is_active == True)
    items = query.order_by(MembershipPlan.created_at.desc()).all()
    return {"items": items, "total": len(items)}


def get_plan_or_404(db: Session, plan_id: uuid.UUID, tenant_id: uuid.UUID) -> MembershipPlan:
    return _get_plan_or_404(db, plan_id, tenant_id)


def update_membership_plan(
    db: Session, plan: MembershipPlan, payload
) -> MembershipPlan:
    """Update allowed fields on a membership plan."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


def deactivate_membership_plan(db: Session, plan: MembershipPlan) -> MembershipPlan:
    """Soft-deactivate a membership plan (cannot deactivate plans with active or frozen memberships)."""
    active_count = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == plan.tenant_id,
            Membership.membership_plan_id == plan.id,
            Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.FROZEN]),
        )
        .count()
    )
    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot deactivate plan: {active_count} active membership(s) use this plan (including frozen memberships)",
        )
    plan.is_active = False
    db.commit()
    db.refresh(plan)
    return plan


# ──────────────────────────────────────────────────────────────────────────────
# Membership CRUD and Lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def create_membership(
    db: Session,
    payload: MembershipCreateRequest,
    current_user: User,
) -> Membership:
    """
    Assign a membership plan to a member.
    Validates member belongs to tenant, plan is active, and no overlapping
    ACTIVE/FROZEN membership exists for the member.
    """
    tenant_id = current_user.tenant_id

    # Validate member belongs to tenant
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Validate plan is active and belongs to tenant
    plan = _get_plan_or_404(db, payload.membership_plan_id, tenant_id)
    if not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected membership plan is inactive",
        )

    # Check for existing overlapping active/frozen membership
    conflicting = (
        db.query(Membership)
        .filter(
            Membership.member_id == payload.member_id,
            Membership.tenant_id == tenant_id,
            Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.FROZEN]),
        )
        .first()
    )
    if conflicting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member already has an active or frozen membership. Renew or cancel it first.",
        )

    end_date = _calculate_end_date(payload.start_date, plan)

    membership = Membership(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=payload.member_id,
        membership_plan_id=payload.membership_plan_id,
        start_date=payload.start_date,
        end_date=end_date,
        status=MembershipStatus.ACTIVE,
        total_frozen_days=0,
        notes=payload.notes,
    )
    try:
        db.add(membership)
        # Set member status to ACTIVE
        member.status = MemberStatus.ACTIVE
        db.commit()
        db.refresh(membership)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership creation failed due to database constraint violation",
        )
    except Exception:
        db.rollback()
        raise

    # Load relationships
    membership = _get_membership_or_404(db, membership.id, tenant_id)
    return membership


def list_memberships(
    db: Session,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    member_id: Optional[uuid.UUID] = None,
    status_filter: Optional[MembershipStatus] = None,
) -> dict:
    """Return paginated memberships for the tenant."""
    # Ensure statuses are up-to-date with current date
    sync_expired_memberships(db, tenant_id)

    query = (
        db.query(Membership)
        .options(joinedload(Membership.member), joinedload(Membership.membership_plan))
        .filter(Membership.tenant_id == tenant_id)
    )
    if member_id:
        query = query.filter(Membership.member_id == member_id)
    if status_filter:
        query = query.filter(Membership.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Membership.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


def freeze_membership(
    db: Session,
    membership: Membership,
    payload: MembershipFreezeRequest,
) -> Membership:
    """
    Freeze an ACTIVE membership immediately.
    Sets freeze dates and transitions status to FROZEN.
    The end_date is extended upon unfreezing by the number of frozen days.
    """
    if membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot freeze a membership with status '{membership.status.value}'",
        )
    today = get_gym_today(db, membership.tenant_id)
    if payload.freeze_start_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Freeze start date cannot be in the past",
        )
    if payload.freeze_start_date > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Freeze start date cannot be in the future; only immediate freeze starting today is currently supported",
        )
    if payload.freeze_start_date < membership.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Freeze start date cannot precede the membership start date",
        )
    if payload.freeze_start_date >= membership.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Freeze start date must be before the membership end date",
        )

    membership.status = MembershipStatus.FROZEN
    membership.freeze_start_date = payload.freeze_start_date
    membership.freeze_end_date = payload.freeze_end_date
    db.commit()
    db.refresh(membership)
    return membership


def unfreeze_membership(
    db: Session,
    membership: Membership,
    unfreeze_date: Optional[date] = None,
) -> Membership:
    """
    Unfreeze a FROZEN membership.
    Calculates actual frozen days using calendar difference convention
    (exclusive of unfreeze date, or calendar days elapsed) and extends end_date.
    """
    if membership.status != MembershipStatus.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unfreeze a membership with status '{membership.status.value}'",
        )

    today = get_gym_today(db, membership.tenant_id)
    effective_unfreeze = unfreeze_date or today

    if membership.freeze_start_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Membership freeze data is inconsistent",
        )
    if effective_unfreeze < membership.freeze_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unfreeze date cannot precede freeze start date",
        )
    if effective_unfreeze > membership.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unfreeze date cannot exceed membership validity end date",
        )

    # Calculate frozen days (capped at scheduled freeze_end_date)
    freeze_end = min(effective_unfreeze, membership.freeze_end_date) if membership.freeze_end_date else effective_unfreeze
    frozen_days = (freeze_end - membership.freeze_start_date).days
    if frozen_days < 0:
        frozen_days = 0

    # Extend end_date
    membership.end_date = membership.end_date + timedelta(days=frozen_days)
    membership.total_frozen_days += frozen_days
    membership.status = MembershipStatus.ACTIVE
    membership.freeze_start_date = None
    membership.freeze_end_date = None

    db.commit()
    db.refresh(membership)
    return membership


def renew_membership(
    db: Session,
    membership: Membership,
    payload: MembershipRenewRequest,
    current_user: User,
) -> Membership:
    """
    Renew an existing membership.
    Creates a new Membership record chained via renewed_from_id. The previous one is cancelled.
    If membership is active, new membership starts the day after current end_date.
    If membership has already expired, new membership defaults to starting today.
    """
    tenant_id = current_user.tenant_id

    if membership.status == MembershipStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot renew a cancelled membership",
        )
    if membership.status == MembershipStatus.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot renew a frozen membership; unfreeze the membership before renewing",
        )

    # Resolve plan
    if payload.membership_plan_id:
        plan = _get_plan_or_404(db, payload.membership_plan_id, tenant_id)
        if not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected plan is inactive",
            )
    else:
        plan = membership.membership_plan

    # Resolve start date
    today = get_gym_today(db, tenant_id)
    if payload.start_date:
        start_date = payload.start_date
    elif membership.status == MembershipStatus.EXPIRED or membership.end_date < today:
        # Default to starting today if old membership has expired
        start_date = today
    else:
        # Seamless renewal: start the day after current active end_date
        start_date = membership.end_date + timedelta(days=1)

    end_date = _calculate_end_date(start_date, plan)

    try:
        # Cancel the old membership
        membership.status = MembershipStatus.CANCELLED
        db.flush()

        new_membership = Membership(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            member_id=membership.member_id,
            membership_plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            status=MembershipStatus.ACTIVE,
            total_frozen_days=0,
            renewed_from_id=membership.id,
            notes=payload.notes,
        )
        db.add(new_membership)

        # Ensure member status is ACTIVE
        member = (
            db.query(Member)
            .filter(Member.id == membership.member_id, Member.tenant_id == tenant_id)
            .first()
        )
        if member:
            member.status = MemberStatus.ACTIVE

        db.commit()
        db.refresh(new_membership)
    except Exception:
        db.rollback()
        raise

    new_membership = _get_membership_or_404(db, new_membership.id, tenant_id)
    return new_membership


def upgrade_membership(
    db: Session,
    membership: Membership,
    payload: MembershipUpgradeRequest,
    current_user: User,
) -> Membership:
    """
    Upgrade or downgrade a membership to a different plan.
    The old membership is cancelled and a new one created from the effective date.
    
    Unresolved Policy Note: Day 2 scope does not implement mid-freeze plan migration,
    remaining-value credit calculation, or freeze-day transfers across different plans.
    Therefore, frozen memberships must be unfrozen prior to executing plan upgrades.
    """
    tenant_id = current_user.tenant_id

    if membership.status == MembershipStatus.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upgrade a frozen membership; please unfreeze the membership before upgrading",
        )
    if membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change plan on a membership with status '{membership.status.value}'",
        )
    if membership.membership_plan_id == payload.new_membership_plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New plan must be different from the current plan",
        )

    new_plan = _get_plan_or_404(db, payload.new_membership_plan_id, tenant_id)
    if not new_plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target plan is inactive",
        )

    today = get_gym_today(db, tenant_id)
    effective_date = payload.effective_date or today
    end_date = _calculate_end_date(effective_date, new_plan)

    try:
        # Cancel old
        membership.status = MembershipStatus.CANCELLED
        db.flush()

        new_membership = Membership(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            member_id=membership.member_id,
            membership_plan_id=new_plan.id,
            start_date=effective_date,
            end_date=end_date,
            status=MembershipStatus.ACTIVE,
            total_frozen_days=0,
            renewed_from_id=membership.id,
            notes=payload.notes or f"Upgraded/changed from plan: {membership.membership_plan_id}",
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
    except Exception:
        db.rollback()
        raise

    new_membership = _get_membership_or_404(db, new_membership.id, tenant_id)
    return new_membership

