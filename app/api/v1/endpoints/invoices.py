"""Invoices REST API endpoints."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.auth import require_role
from app.core.database import get_db
from app.models.invoice import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoices import (
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
    InvoiceCancelRequest,
    InvoiceResponse,
    InvoiceListResponse,
    OutstandingDuesResponse,
)
from app.services import invoice_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_MANAGE_ROLES = (UserRole.OWNER, UserRole.MANAGER)


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Invoice",
    description="Create a new billing invoice strictly isolated to the authenticated gym tenant.",
)
async def create_invoice(
    payload: InvoiceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> InvoiceResponse:
    invoice = invoice_service.create_invoice(db, current_user.tenant_id, payload)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Invoices",
    description="Return paginated list of billing invoices with optional filters.",
)
async def list_invoices(
    member_id: Optional[UUID] = Query(None, description="Filter by member UUID"),
    invoice_status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, description="Filter issue date on or after YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Filter issue date on or before YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> InvoiceListResponse:
    return invoice_service.list_invoices(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        invoice_status=invoice_status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/outstanding",
    response_model=OutstandingDuesResponse,
    status_code=status.HTTP_200_OK,
    summary="Outstanding Dues",
    description="Calculate outstanding dues across the tenant or for a specific member.",
)
async def get_outstanding_dues(
    member_id: Optional[UUID] = Query(None, description="Optional member UUID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> OutstandingDuesResponse:
    return invoice_service.get_outstanding_dues(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
    )


@router.get(
    "/member/{member_id}",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Member Invoices",
    description="Retrieve all invoices for a specific member.",
)
async def get_member_invoices(
    member_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> InvoiceListResponse:
    return invoice_service.list_invoices(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Invoice",
    description="Retrieve invoice details by invoice UUID.",
)
async def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> InvoiceResponse:
    invoice = invoice_service.get_invoice(db, current_user.tenant_id, invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Invoice",
    description="Update permitted fields (due_date, description) of an existing invoice.",
)
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> InvoiceResponse:
    invoice = invoice_service.update_invoice(db, current_user.tenant_id, invoice_id, payload)
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Invoice",
    description="Cancel an invoice if no paid amounts exist against it.",
)
async def cancel_invoice(
    invoice_id: UUID,
    payload: Optional[InvoiceCancelRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> InvoiceResponse:
    invoice = invoice_service.cancel_invoice(db, current_user.tenant_id, invoice_id, payload)
    return InvoiceResponse.model_validate(invoice)

