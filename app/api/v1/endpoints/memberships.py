"""Memberships REST API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.membership import MembershipStatus
from app.models.user import User, UserRole
from app.schemas.memberships import (
    MembershipCreateRequest,
    MembershipFreezeRequest,
    MembershipListResponse,
    MembershipRenewRequest,
    MembershipResponse,
    MembershipUnfreezeRequest,
    MembershipUpgradeRequest,
)
from app.services import membership_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)


@router.post(
    "",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Membership",
    description="Assign a membership plan to a member. Auto-calculates end date.",
)
async def create_membership(
    payload: MembershipCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipResponse:
    return membership_service.create_membership(db, payload, current_user)


@router.get(
    "",
    response_model=MembershipListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Memberships",
    description="Return a paginated list of memberships for the gym.",
)
async def list_memberships(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member_id: Optional[UUID] = Query(None, description="Filter by member"),
    membership_status: Optional[MembershipStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MembershipListResponse:
    result = membership_service.list_memberships(
        db,
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        member_id=member_id,
        status_filter=membership_status,
    )
    return MembershipListResponse(**result)


@router.get(
    "/{membership_id}",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Membership",
    description="Retrieve a specific membership record.",
)
async def get_membership(
    membership_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MembershipResponse:
    return membership_service._get_membership_or_404(db, membership_id, current_user.tenant_id)


@router.post(
    "/{membership_id}/freeze",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Freeze Membership",
    description="Freeze an active membership for a specified date range.",
)
async def freeze_membership(
    membership_id: UUID,
    payload: MembershipFreezeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipResponse:
    membership = membership_service._get_membership_or_404(db, membership_id, current_user.tenant_id)
    return membership_service.freeze_membership(db, membership, payload)


@router.post(
    "/{membership_id}/unfreeze",
    response_model=MembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Unfreeze Membership",
    description="Unfreeze a frozen membership. End date is extended by the frozen days.",
)
async def unfreeze_membership(
    membership_id: UUID,
    payload: MembershipUnfreezeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipResponse:
    membership = membership_service._get_membership_or_404(db, membership_id, current_user.tenant_id)
    return membership_service.unfreeze_membership(db, membership, payload.unfreeze_date)


@router.post(
    "/{membership_id}/renew",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Renew Membership",
    description="Renew a membership. Optionally switch to a different plan.",
)
async def renew_membership(
    membership_id: UUID,
    payload: MembershipRenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipResponse:
    membership = membership_service._get_membership_or_404(db, membership_id, current_user.tenant_id)
    return membership_service.renew_membership(db, membership, payload, current_user)


@router.post(
    "/{membership_id}/upgrade",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upgrade / Downgrade Membership",
    description="Change a membership to a different plan from the effective date.",
)
async def upgrade_membership(
    membership_id: UUID,
    payload: MembershipUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MembershipResponse:
    membership = membership_service._get_membership_or_404(db, membership_id, current_user.tenant_id)
    return membership_service.upgrade_membership(db, membership, payload, current_user)

