"""Receipts REST API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.auth import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.receipts import ReceiptCreateRequest, ReceiptResponse
from app.services import payment_service

router = APIRouter()

_READ_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)
_STAFF_ROLES = (UserRole.OWNER, UserRole.MANAGER, UserRole.FRONT_DESK)


@router.get(
    "/payment/{payment_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Receipt by Payment",
    description="Retrieve the issued receipt for a specific payment UUID.",
)
async def get_receipt_by_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> ReceiptResponse:
    receipt = payment_service.get_receipt_by_payment(db, current_user.tenant_id, payment_id)
    resp = ReceiptResponse.model_validate(receipt)
    if receipt.payment:
        resp.amount_paise = receipt.payment.amount_paise
        resp.payment_method = receipt.payment.payment_method.value
        resp.member_id = receipt.payment.member_id
        resp.invoice_id = receipt.payment.invoice_id
    return resp


@router.post(
    "/payment/{payment_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Receipt",
    description="Manually generate a receipt for a completed payment if not auto-generated.",
)
async def generate_receipt(
    payment_id: UUID,
    payload: Optional[ReceiptCreateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_STAFF_ROLES)),
) -> ReceiptResponse:
    notes = payload.notes if payload else None
    receipt = payment_service.generate_receipt(
        db=db,
        tenant_id=current_user.tenant_id,
        payment_id=payment_id,
        notes=notes,
    )
    resp = ReceiptResponse.model_validate(receipt)
    if receipt.payment:
        resp.amount_paise = receipt.payment.amount_paise
        resp.payment_method = receipt.payment.payment_method.value
        resp.member_id = receipt.payment.member_id
        resp.invoice_id = receipt.payment.invoice_id
    return resp


@router.get(
    "/{receipt_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Receipt",
    description="Retrieve receipt details by receipt UUID.",
)
async def get_receipt(
    receipt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_READ_ROLES)),
) -> ReceiptResponse:
    receipt = payment_service.get_receipt(db, current_user.tenant_id, receipt_id)
    resp = ReceiptResponse.model_validate(receipt)
    if receipt.payment:
        resp.amount_paise = receipt.payment.amount_paise
        resp.payment_method = receipt.payment.payment_method.value
        resp.member_id = receipt.payment.member_id
        resp.invoice_id = receipt.payment.invoice_id
    return resp

