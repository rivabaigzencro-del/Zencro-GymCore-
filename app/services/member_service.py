"""Member service — business logic for member registration and management."""
import math
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.member import Member, MemberStatus
from app.models.user import User
from app.schemas.members import MemberCreateRequest, MemberUpdateRequest
from app.services.membership_service import sync_expired_memberships
from app.services.audit_service import log_audit_event


def create_member(
    db: Session,
    payload: MemberCreateRequest,
    current_user: User,
) -> Member:
    """
    Register a new gym member scoped to the authenticated user's tenant.
    Validates uniqueness of phone (required) and email (when provided) within the tenant.
    """
    tenant_id = current_user.tenant_id

    # Phone uniqueness within tenant (phone is the primary deduplication key)
    if payload.phone:
        existing_phone = (
            db.query(Member)
            .filter(Member.tenant_id == tenant_id, Member.phone == payload.phone)
            .first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A member with phone '{payload.phone}' already exists in this gym",
            )

    # Email uniqueness within tenant (when provided)
    if payload.email:
        existing_email = (
            db.query(Member)
            .filter(Member.tenant_id == tenant_id, Member.email == payload.email)
            .first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A member with email '{payload.email}' already exists in this gym",
            )

    member = Member(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        gender=payload.gender,
        date_of_birth=payload.date_of_birth,
        address=payload.address,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        status=MemberStatus.ACTIVE,
    )
    try:
        db.add(member)
        db.commit()
        db.refresh(member)
        return member
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this phone or email already exists in this gym",
        )
    except Exception:
        db.rollback()
        raise


def get_member_or_404(db: Session, member_id: uuid.UUID, tenant_id: uuid.UUID) -> Member:
    """Retrieve a member by ID scoped to the tenant, raising 404 if not found."""
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    return member


def list_members(
    db: Session,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status_filter: Optional[MemberStatus] = None,
) -> dict:
    """
    Return a paginated, optionally filtered list of members for the tenant.
    Search matches against full_name, email and phone.
    """
    # Ensure statuses are synchronized with actual dates
    sync_expired_memberships(db, tenant_id)

    query = db.query(Member).filter(Member.tenant_id == tenant_id)

    if search:
        cleaned_search = search.strip()
        search_term = f"%{cleaned_search}%"
        query = query.filter(
            Member.full_name.ilike(search_term)
            | Member.email.ilike(search_term)
            | Member.phone.ilike(search_term)
        )

    if status_filter:
        query = query.filter(Member.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Member.created_at.desc())
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


def update_member(
    db: Session,
    member: Member,
    payload: MemberUpdateRequest,
    tenant_id: uuid.UUID,
    current_user: Optional[User] = None,
) -> Member:
    """
    Update allowed fields of a member record.
    Re-validates email/phone uniqueness when those fields change.
    """
    update_data = payload.model_dump(exclude_unset=True)

    # Re-validate phone uniqueness if changing
    if "phone" in update_data and update_data["phone"] != member.phone:
        existing = (
            db.query(Member)
            .filter(
                Member.tenant_id == tenant_id,
                Member.phone == update_data["phone"],
                Member.id != member.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phone '{update_data['phone']}' is already registered to another member",
            )

    # Re-validate email uniqueness if changing
    if "email" in update_data and update_data["email"] and update_data["email"] != member.email:
        existing = (
            db.query(Member)
            .filter(
                Member.tenant_id == tenant_id,
                Member.email == update_data["email"],
                Member.id != member.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{update_data['email']}' is already registered to another member",
            )

    before_values = {k: getattr(member, k) for k in update_data.keys()}

    try:
        for field, value in update_data.items():
            setattr(member, field, value)

        after_values = {k: getattr(member, k) for k in update_data.keys()}

        log_audit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id if current_user else None,
            action="MEMBER_UPDATE",
            resource_type="MEMBER",
            resource_id=str(member.id),
            before_values=before_values,
            after_values=after_values,
            reason="Member profile updated",
        )

        db.commit()
        db.refresh(member)
        return member
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this phone or email already exists in this gym",
        )
    except Exception:
        db.rollback()
        raise


def delete_member(db: Session, member: Member, current_user: Optional[User] = None) -> None:
    """
    Soft-delete a member by setting status to INACTIVE.
    Hard delete is not performed to preserve membership history integrity.
    """
    before_status = member.status.value
    member.status = MemberStatus.INACTIVE

    log_audit_event(
        db=db,
        tenant_id=member.tenant_id,
        user_id=current_user.id if current_user else None,
        action="MEMBER_STATUS_CHANGE",
        resource_type="MEMBER",
        resource_id=str(member.id),
        before_values={"status": before_status},
        after_values={"status": MemberStatus.INACTIVE.value},
        reason="Member deactivated",
    )

    db.commit()

