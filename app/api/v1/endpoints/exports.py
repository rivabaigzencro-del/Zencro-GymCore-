"""Exports REST API endpoints — CSV and Excel data downloads."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services import export_service

router = APIRouter()

# Financial data export roles (strictly Owner and Manager)
_FINANCIAL_ROLES = (UserRole.OWNER, UserRole.MANAGER)
# General operational data export roles
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)


@router.get(
    "/members",
    status_code=status.HTTP_200_OK,
    summary="Export Member Records",
    description="Download member records in CSV (.csv) or Excel (.xlsx) format.",
    response_class=Response,
)
def export_members(
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: 'csv' or 'xlsx'"),
    is_active: Optional[bool] = Query(None, description="Filter by active/inactive members"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> Response:
    content, media_type, filename = export_service.export_members(
        db,
        current_user.tenant_id,
        is_active=is_active,
        export_format=format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/memberships",
    status_code=status.HTTP_200_OK,
    summary="Export Membership Records",
    description="Download membership subscription records in CSV (.csv) or Excel (.xlsx) format.",
    response_class=Response,
)
def export_memberships(
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: 'csv' or 'xlsx'"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, EXPIRED, FROZEN, CANCELLED"),
    start_date: Optional[date] = Query(None, description="Filter memberships starting on or after date"),
    end_date: Optional[date] = Query(None, description="Filter memberships starting on or before date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> Response:
    content, media_type, filename = export_service.export_memberships(
        db,
        current_user.tenant_id,
        status_filter=status,
        start_date=start_date,
        end_date=end_date,
        export_format=format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/payments",
    status_code=status.HTTP_200_OK,
    summary="Export Payment Records",
    description="Download payment collection transactions in CSV (.csv) or Excel (.xlsx) format.",
    response_class=Response,
)
def export_payments(
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: 'csv' or 'xlsx'"),
    payment_method: Optional[str] = Query(None, description="Filter by method: CASH, UPI, CARD, BANK_TRANSFER, CHEQUE"),
    start_date: Optional[date] = Query(None, description="Filter payments recorded on or after date"),
    end_date: Optional[date] = Query(None, description="Filter payments recorded on or before date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_FINANCIAL_ROLES)),
) -> Response:
    content, media_type, filename = export_service.export_payments(
        db,
        current_user.tenant_id,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
        export_format=format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/attendance",
    status_code=status.HTTP_200_OK,
    summary="Export Attendance Records",
    description="Download gym attendance visit records in CSV (.csv) or Excel (.xlsx) format.",
    response_class=Response,
)
def export_attendance(
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: 'csv' or 'xlsx'"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    member_id: Optional[UUID] = Query(None, description="Filter visits for specific member"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> Response:
    content, media_type, filename = export_service.export_attendance(
        db,
        current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        member_id=member_id,
        export_format=format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/reports/{report_type}",
    status_code=status.HTTP_200_OK,
    summary="Export Reports (CSV/Excel)",
    description="Download generated report data (revenue, memberships, attendance, pending-dues, expiries).",
    response_class=Response,
)
def export_report(
    report_type: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: 'csv' or 'xlsx'"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    filter_val: Optional[str] = Query(None, description="Secondary filter (payment_method, status, or ageing_bucket)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> Response:
    # If exporting financial reports (revenue or dues), require OWNER or MANAGER
    if report_type.lower() in ("revenue", "collections", "pending-dues", "dues"):
        if current_user.role not in _FINANCIAL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Financial reports export requires Owner or Manager privileges",
            )

    content, media_type, filename = export_service.export_report(
        db,
        current_user.tenant_id,
        report_type=report_type,
        export_format=format,
        start_date=start_date,
        end_date=end_date,
        filter_val=filter_val,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

