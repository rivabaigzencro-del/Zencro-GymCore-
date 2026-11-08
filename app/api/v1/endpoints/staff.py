"""Staff Management API Endpoints for GYMCORE."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.staff import (
    StaffCreateRequest,
    StaffListResponse,
    StaffResponse,
    StaffRoleUpdateRequest,
    StaffStatusUpdateRequest,
    StaffUpdateRequest,
)
from app.services import staff_service

router = APIRouter()

_VIEW_ROLES = (UserRole.OWNER, UserRole.MANAGER)
_EDIT_ROLES = (UserRole.OWNER, UserRole.MANAGER)
_OWNER_ONLY = (UserRole.OWNER,)


@router.get(
    "",
    response_model=StaffListResponse,
    summary="List Staff Members",
    description="Retrieve paginated list of staff members for the current gym. Requires OWNER or MANAGER role.",
)
async def list_staff_members(
    role: Optional[UserRole] = Query(None, description="Filter by staff role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_VIEW_ROLES)),
) -> StaffListResponse:
    res = staff_service.list_staff(
        db=db,
        tenant_id=current_user.tenant_id,
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )
    return StaffListResponse(
        items=[StaffResponse.model_validate(u) for u in res["items"]],
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
        pages=res["pages"],
    )


@router.post(
    "",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Staff Member",
    description="Create a new staff member (MANAGER or FRONT_DESK). Managers can only create Front Desk staff.",
)
async def create_staff_member(
    payload: StaffCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_EDIT_ROLES)),
) -> StaffResponse:
    new_staff = staff_service.create_staff(
        db=db,
        current_user=current_user,
        payload=payload,
        request=request,
    )
    return StaffResponse.model_validate(new_staff)


@router.get(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Get Staff Member",
    description="Retrieve details of a staff member by ID. Requires OWNER or MANAGER role.",
)
async def get_staff_member(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_VIEW_ROLES)),
) -> StaffResponse:
    staff = staff_service.get_staff_or_404(
        db=db,
        staff_id=staff_id,
        tenant_id=current_user.tenant_id,
    )
    return StaffResponse.model_validate(staff)


@router.patch(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Update Staff Profile",
    description="Update staff profile details (name, phone, email). Managers cannot modify Owner accounts.",
)
async def update_staff_member(
    staff_id: UUID,
    payload: StaffUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_EDIT_ROLES)),
) -> StaffResponse:
    updated_staff = staff_service.update_staff(
        db=db,
        current_user=current_user,
        staff_id=staff_id,
        payload=payload,
        request=request,
    )
    return StaffResponse.model_validate(updated_staff)


@router.patch(
    "/{staff_id}/status",
    response_model=StaffResponse,
    summary="Update Staff Active Status",
    description="Activate or deactivate a staff member. Prevents self-deactivation and preserves last active Owner.",
)
async def update_staff_status(
    staff_id: UUID,
    payload: StaffStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_EDIT_ROLES)),
) -> StaffResponse:
    updated_staff = staff_service.update_staff_status(
        db=db,
        current_user=current_user,
        staff_id=staff_id,
        payload=payload,
        request=request,
    )
    return StaffResponse.model_validate(updated_staff)


@router.patch(
    "/{staff_id}/role",
    response_model=StaffResponse,
    summary="Update Staff Role",
    description="Change a staff member's role. Restricted strictly to OWNER. Cannot promote to OWNER.",
)
async def update_staff_role(
    staff_id: UUID,
    payload: StaffRoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_OWNER_ONLY)),
) -> StaffResponse:
    updated_staff = staff_service.update_staff_role(
        db=db,
        current_user=current_user,
        staff_id=staff_id,
        payload=payload,
        request=request,
    )
    return StaffResponse.model_validate(updated_staff)

