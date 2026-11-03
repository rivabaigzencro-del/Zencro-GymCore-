"""Membership Plans REST API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.membership_plans import (
    MembershipPlanCreateRequest,
    MembershipPlanListResponse,
    MembershipPlanResponse,
    MembershipPlanUpdateRequest,
)
from app.services import membership_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_WRITE_ROLES = (UserRole.OWNER, UserRole.MANAGER)


@router.post(
    "",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Membership Plan",
    description="Create a new membership plan for the gym.",
)
async def create_plan(
    payload: MembershipPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> MembershipPlanResponse:
    return membership_service.create_membership_plan(db, payload, current_user)


@router.get(
    "",
    response_model=MembershipPlanListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Membership Plans",
    description="List all membership plans for the gym. Pass include_inactive=true to see deactivated plans.",
)
async def list_plans(
    include_inactive: bool = Query(False, description="Include inactive plans"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MembershipPlanListResponse:
    result = membership_service.list_membership_plans(
        db,
        tenant_id=current_user.tenant_id,
        include_inactive=include_inactive,
    )
    return MembershipPlanListResponse(**result)


@router.get(
    "/{plan_id}",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Membership Plan",
    description="Retrieve details of a specific membership plan.",
)
async def get_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MembershipPlanResponse:
    return membership_service.get_plan_or_404(db, plan_id, current_user.tenant_id)


@router.put(
    "/{plan_id}",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Membership Plan",
    description="Update a membership plan's details.",
)
async def update_plan(
    plan_id: UUID,
    payload: MembershipPlanUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> MembershipPlanResponse:
    plan = membership_service.get_plan_or_404(db, plan_id, current_user.tenant_id)
    return membership_service.update_membership_plan(db, plan, payload)


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Membership Plan",
    description="Deactivate a membership plan. Cannot deactivate plans with active memberships.",
)
async def deactivate_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
) -> dict:
    plan = membership_service.get_plan_or_404(db, plan_id, current_user.tenant_id)
    membership_service.deactivate_membership_plan(db, plan)
    return {"message": "Membership plan deactivated", "plan_id": str(plan_id)}

