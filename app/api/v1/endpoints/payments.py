"""Payments REST API endpoints."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.auth import require_role
from app.core.database import get_db
from app.models.payment import PaymentMethod, PaymentStatus
from app.models.user import User, UserRole
from app.schemas.payments import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentListResponse,
    RefundRequest,
    ReversalRequest,
    RefundResponse,
    DailySummaryResponse,
)
from app.services import payment_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_MANAGE_ROLES = (UserRole.OWNER, UserRole.MANAGER)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Payment",
    description="Record a payment transaction against an invoice or member. Auto-generates receipt if requested.",
)
async def record_payment(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> PaymentResponse:
    payment = payment_service.record_payment(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
        user_id=current_user.id,
    )
    resp = PaymentResponse.model_validate(payment)
    if payment.receipt:
        resp.receipt_number = payment.receipt.receipt_number
        resp.receipt_id = payment.receipt.id
    return resp


@router.get(
    "",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Payments",
    description="Return paginated list of payment transactions strictly scoped to the tenant.",
)
async def list_payments(
    member_id: Optional[UUID] = Query(None, description="Filter by member UUID"),
    invoice_id: Optional[UUID] = Query(None, description="Filter by invoice UUID"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter by method"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, description="Filter date on or after YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Filter date on or before YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> PaymentListResponse:
    return payment_service.list_payments(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        invoice_id=invoice_id,
        payment_method=payment_method,
        payment_status=payment_status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/daily-summary",
    response_model=DailySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Daily Close Summary",
    description="Generate daily financial collections summary broken down by payment method and net totals.",
)
async def get_daily_summary(
    target_date: Optional[date] = Query(None, description="Target business date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> DailySummaryResponse:
    return payment_service.get_daily_summary(
        db=db,
        tenant_id=current_user.tenant_id,
        target_date=target_date,
    )


@router.get(
    "/member/{member_id}",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Member Payments",
    description="Retrieve all payments made by a specific member.",
)
async def get_member_payments(
    member_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> PaymentListResponse:
    return payment_service.list_payments(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/invoice/{invoice_id}",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Invoice Payments",
    description="Retrieve all payments applied against a specific invoice.",
)
async def get_invoice_payments(
    invoice_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> PaymentListResponse:
    return payment_service.list_payments(
        db=db,
        tenant_id=current_user.tenant_id,
        invoice_id=invoice_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Payment",
    description="Retrieve payment transaction details by UUID.",
)
async def get_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> PaymentResponse:
    payment = payment_service.get_payment(db, current_user.tenant_id, payment_id)
    resp = PaymentResponse.model_validate(payment)
    if payment.receipt:
        resp.receipt_number = payment.receipt.receipt_number
        resp.receipt_id = payment.receipt.id
    return resp


@router.post(
    "/{payment_id}/refund",
    response_model=RefundResponse,
    status_code=status.HTTP_200_OK,
    summary="Refund Payment",
    description="Process a full or partial refund for a completed payment. Updates invoice balance atomically.",
)
async def refund_payment(
    payment_id: UUID,
    payload: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> RefundResponse:
    refund = payment_service.refund_payment(
        db=db,
        tenant_id=current_user.tenant_id,
        payment_id=payment_id,
        payload=payload,
        initiated_by_id=current_user.id,
    )
    return RefundResponse.model_validate(refund)


@router.post(
    "/{payment_id}/reverse",
    response_model=RefundResponse,
    status_code=status.HTTP_200_OK,
    summary="Reverse Payment",
    description="Reverse a payment transaction (e.g. bounced cheque, disputed charge). Re-adjusts invoice balance.",
)
async def reverse_payment(
    payment_id: UUID,
    payload: ReversalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_MANAGE_ROLES)),
) -> RefundResponse:
    reversal = payment_service.reverse_payment(
        db=db,
        tenant_id=current_user.tenant_id,
        payment_id=payment_id,
        payload=payload,
        initiated_by_id=current_user.id,
    )
    return RefundResponse.model_validate(reversal)

