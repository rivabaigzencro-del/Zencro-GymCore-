"""Staff Management Service for GYMCORE.

Handles staff listing, creation, updates, activation/deactivation, and role changes.
Enforces strict RBAC hierarchy:
- OWNER: can manage MANAGER and FRONT_DESK, change roles, activate/deactivate.
- MANAGER: can view staff, create and manage FRONT_DESK. Cannot modify OWNER accounts.
- FRONT_DESK: no access to staff management.
- Self-deactivation prevention and last active OWNER protection.
- Emits audit log events for all staff operations.
"""
import math
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.staff import (
    StaffCreateRequest,
    StaffRoleUpdateRequest,
    StaffStatusUpdateRequest,
    StaffUpdateRequest,
)
from app.services.audit_service import log_audit_event


def list_staff(
    db: Session,
    tenant_id: UUID,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """List staff members with pagination, role filtering, active status, and search."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = db.query(User).filter(User.tenant_id == tenant_id)

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )

    total = query.count()
    pages = math.ceil(total / page_size) if total > 0 else 1

    items = (
        query.order_by(desc(User.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def get_staff_or_404(db: Session, staff_id: UUID, tenant_id: UUID) -> User:
    """Retrieve a staff member ensuring strict tenant isolation."""
    staff = db.query(User).filter(User.id == staff_id, User.tenant_id == tenant_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member with ID {staff_id} not found",
        )
    return staff


def create_staff(
    db: Session,
    current_user: User,
    payload: StaffCreateRequest,
    request: Optional[Request] = None,
) -> User:
    """Create a new staff member (MANAGER or FRONT_DESK).

    Enforces RBAC hierarchy and prevents duplicate emails.
    """
    # RBAC hierarchy check
    if current_user.role == UserRole.MANAGER and payload.role != UserRole.FRONT_DESK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers are only permitted to create Front Desk staff accounts",
        )

    if payload.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create an Owner account through staff management",
        )

    # Check for existing user with identical email
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with email '{payload.email}' already exists",
        )

    new_staff = User(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_staff)
    db.flush()

    # Log audit event
    log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="STAFF_CREATE",
        resource_type="USER",
        resource_id=str(new_staff.id),
        after_values={
            "name": new_staff.name,
            "email": new_staff.email,
            "role": new_staff.role.value,
            "is_active": new_staff.is_active,
        },
        reason="New staff account created",
        request=request,
    )

    db.commit()
    db.refresh(new_staff)
    return new_staff


def update_staff(
    db: Session,
    current_user: User,
    staff_id: UUID,
    payload: StaffUpdateRequest,
    request: Optional[Request] = None,
) -> User:
    """Update staff profile details."""
    target_staff = get_staff_or_404(db, staff_id, current_user.tenant_id)

    # RBAC check: Manager cannot modify Owner accounts
    if current_user.role == UserRole.MANAGER and target_staff.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers cannot modify Owner accounts",
        )

    # Check email uniqueness if email is changed
    if payload.email and payload.email != target_staff.email:
        existing_email = (
            db.query(User)
            .filter(User.email == payload.email, User.id != target_staff.id)
            .first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{payload.email}' is already in use by another user",
            )

    before_values = {
        "name": target_staff.name,
        "email": target_staff.email,
        "phone": target_staff.phone,
    }

    if payload.name is not None:
        target_staff.name = payload.name
    if payload.phone is not None:
        target_staff.phone = payload.phone
    if payload.email is not None:
        target_staff.email = payload.email

    after_values = {
        "name": target_staff.name,
        "email": target_staff.email,
        "phone": target_staff.phone,
    }

    log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="STAFF_UPDATE",
        resource_type="USER",
        resource_id=str(target_staff.id),
        before_values=before_values,
        after_values=after_values,
        reason="Staff profile updated",
        request=request,
    )

    db.commit()
    db.refresh(target_staff)
    return target_staff


def update_staff_status(
    db: Session,
    current_user: User,
    staff_id: UUID,
    payload: StaffStatusUpdateRequest,
    request: Optional[Request] = None,
) -> User:
    """Activate or deactivate a staff member.

    Prevents self-deactivation and preserves the last active Owner.
    """
    target_staff = get_staff_or_404(db, staff_id, current_user.tenant_id)

    # RBAC: Manager cannot deactivate Owner
    if current_user.role == UserRole.MANAGER and target_staff.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers cannot change status of Owner accounts",
        )

    # Self-deactivation prevention
    if target_staff.id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    # Protect last active Owner
    if target_staff.role == UserRole.OWNER and not payload.is_active:
        active_owners_count = (
            db.query(User)
            .filter(
                User.tenant_id == current_user.tenant_id,
                User.role == UserRole.OWNER,
                User.is_active == True,
            )
            .count()
        )
        if active_owners_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the only active Owner account for this gym",
            )

    before_values = {"is_active": target_staff.is_active}
    target_staff.is_active = payload.is_active
    after_values = {"is_active": target_staff.is_active}

    log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="STAFF_STATUS_CHANGE",
        resource_type="USER",
        resource_id=str(target_staff.id),
        before_values=before_values,
        after_values=after_values,
        reason=payload.reason or ("Staff activated" if payload.is_active else "Staff deactivated"),
        request=request,
    )

    db.commit()
    db.refresh(target_staff)
    return target_staff


def update_staff_role(
    db: Session,
    current_user: User,
    staff_id: UUID,
    payload: StaffRoleUpdateRequest,
    request: Optional[Request] = None,
) -> User:
    """Update the role of a staff member (OWNER only).

    Prevents assigning OWNER role and demoting the only active Owner.
    """
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only gym owners are authorized to change staff roles",
        )

    if payload.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot promote staff to Owner role",
        )

    target_staff = get_staff_or_404(db, staff_id, current_user.tenant_id)

    # If target is currently an Owner, check if demoting would leave 0 active Owners
    if target_staff.role == UserRole.OWNER and payload.role != UserRole.OWNER:
        active_owners_count = (
            db.query(User)
            .filter(
                User.tenant_id == current_user.tenant_id,
                User.role == UserRole.OWNER,
                User.is_active == True,
            )
            .count()
        )
        if active_owners_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change the role of the only active Owner account",
            )

    before_values = {"role": target_staff.role.value}
    target_staff.role = payload.role
    after_values = {"role": target_staff.role.value}

    log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="STAFF_ROLE_CHANGE",
        resource_type="USER",
        resource_id=str(target_staff.id),
        before_values=before_values,
        after_values=after_values,
        reason=payload.reason or f"Role updated to {payload.role.value}",
        request=request,
    )

    db.commit()
    db.refresh(target_staff)
    return target_staff

