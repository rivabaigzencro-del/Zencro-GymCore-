"""Imports REST API endpoints — CSV and Excel bulk data uploads."""
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.imports import ImportSummaryResponse
from app.services import import_service

router = APIRouter()

# Data import is an administrative capability restricted to Owner and Manager
_ADMIN_ROLES = (UserRole.OWNER, UserRole.MANAGER)


@router.post(
    "/members",
    response_model=ImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Members (CSV/Excel)",
    description="Bulk import member records from CSV (.csv) or Excel (.xlsx) file with deduplication and row-level validation.",
)
async def import_members(
    file: UploadFile = File(..., description="CSV or Excel file with member records"),
    dry_run: bool = Query(False, description="If true, validates data without inserting records"),
    allow_partial: bool = Query(False, description="If true, imports valid rows even if other rows have errors"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ADMIN_ROLES)),
) -> ImportSummaryResponse:
    content = await file.read()
    return import_service.import_members(
        db=db,
        tenant_id=current_user.tenant_id,
        file_bytes=content,
        filename=file.filename or "members.csv",
        dry_run=dry_run,
        allow_partial=allow_partial,
    )


@router.post(
    "/memberships",
    response_model=ImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Memberships (CSV/Excel)",
    description="Bulk import membership subscriptions from CSV or Excel with plan and member resolution.",
)
async def import_memberships(
    file: UploadFile = File(..., description="CSV or Excel file with membership subscription records"),
    dry_run: bool = Query(False, description="If true, validates data without inserting records"),
    allow_partial: bool = Query(False, description="If true, imports valid rows even if other rows have errors"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ADMIN_ROLES)),
) -> ImportSummaryResponse:
    content = await file.read()
    return import_service.import_memberships(
        db=db,
        tenant_id=current_user.tenant_id,
        file_bytes=content,
        filename=file.filename or "memberships.csv",
        dry_run=dry_run,
        allow_partial=allow_partial,
    )


@router.post(
    "/payments",
    response_model=ImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Payments (CSV/Excel)",
    description="Bulk import fee collections from CSV or Excel, updating invoice balances and generating receipts.",
)
async def import_payments(
    file: UploadFile = File(..., description="CSV or Excel file with payment collection records"),
    dry_run: bool = Query(False, description="If true, validates data without inserting records"),
    allow_partial: bool = Query(False, description="If true, imports valid rows even if other rows have errors"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ADMIN_ROLES)),
) -> ImportSummaryResponse:
    content = await file.read()
    return import_service.import_payments(
        db=db,
        tenant_id=current_user.tenant_id,
        file_bytes=content,
        filename=file.filename or "payments.csv",
        dry_run=dry_run,
        allow_partial=allow_partial,
    )

