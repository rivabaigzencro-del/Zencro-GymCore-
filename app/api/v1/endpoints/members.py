"""Members REST API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.member import MemberStatus
from app.models.user import User, UserRole
from app.schemas.members import (
    MemberCreateRequest,
    MemberListResponse,
    MemberResponse,
    MemberUpdateRequest,
)
from app.services import member_service

router = APIRouter()

# Roles that can read members
_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
# Roles that can register and edit members (staff operations)
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
# Roles that can delete/deactivate members (administrative operations)
_ADMIN_ROLES = (UserRole.OWNER, UserRole.MANAGER)


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Member",
    description="Create a new gym member record scoped to the authenticated user's gym.",
)
async def create_member(
    payload: MemberCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MemberResponse:
    return member_service.create_member(db, payload, current_user)


@router.get(
    "",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Members",
    description="Return a paginated, searchable list of members for the authenticated gym.",
)
async def list_members(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email or phone"),
    member_status: Optional[MemberStatus] = Query(None, description="Filter by member status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MemberListResponse:
    result = member_service.list_members(
        db,
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=member_status,
    )
    return MemberListResponse(**result)


@router.get(
    "/search",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Members",
    description="Dedicated search endpoint for member lookup.",
)
async def search_members(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MemberListResponse:
    result = member_service.list_members(
        db,
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        search=q,
    )
    return MemberListResponse(**result)


@router.get(
    "/{member_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Member Profile",
    description="Retrieve a single member's full profile.",
)
async def get_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> MemberResponse:
    return member_service.get_member_or_404(db, member_id, current_user.tenant_id)


@router.put(
    "/{member_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Member",
    description="Update a gym member's information.",
)
async def update_member(
    member_id: UUID,
    payload: MemberUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> MemberResponse:
    member = member_service.get_member_or_404(db, member_id, current_user.tenant_id)
    return member_service.update_member(db, member, payload, current_user.tenant_id, current_user=current_user)


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Member",
    description="Soft-deactivate a member (sets status to INACTIVE). Membership history is preserved.",
)
async def delete_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
) -> dict:
    member = member_service.get_member_or_404(db, member_id, current_user.tenant_id)
    member_service.delete_member(db, member, current_user=current_user)
    return {"message": "Member deactivated successfully", "member_id": str(member_id)}

