"""Payment service — business logic for payments, receipts, refunds, reversals, and financial summaries."""
import math
import uuid
from datetime import date, datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.member import Member
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.receipt import Receipt
from app.models.refund import Refund, RefundType, RefundStatus
from app.schemas.payments import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentListResponse,
    RefundRequest,
    ReversalRequest,
    RefundResponse,
    DailySummaryResponse,
)
from app.schemas.receipts import ReceiptResponse
from app.services.invoice_service import get_gym_today


def _get_tenant_tz(db: Session, tenant_id: uuid.UUID) -> str:
    """Retrieve tenant timezone, defaulting to Asia/Kolkata."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.timezone:
        return tenant.timezone
    return "Asia/Kolkata"


def _generate_receipt_number(db: Session, tenant_id: uuid.UUID) -> str:
    """
    Generate sequentially unique receipt number for the tenant.
    Format: REC-{YYYYMM}-{seq:04d}
    Queries highest existing sequence number with this prefix to prevent collision.
    """
    today = get_gym_today(db, tenant_id)
    prefix = f"REC-{today.strftime('%Y%m')}-"

    last_record = (
        db.query(Receipt.receipt_number)
        .filter(
            Receipt.tenant_id == tenant_id,
            Receipt.receipt_number.like(f"{prefix}%"),
        )
        .order_by(Receipt.receipt_number.desc())
        .first()
    )

    if last_record and last_record[0]:
        try:
            seq = int(last_record[0].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    while True:
        candidate = f"{prefix}{seq:04d}"
        exists = (
            db.query(Receipt.id)
            .filter(Receipt.tenant_id == tenant_id, Receipt.receipt_number == candidate)
            .first()
        )
        if not exists:
            return candidate
        seq += 1


def record_payment(
    db: Session,
    tenant_id: uuid.UUID,
    payload: PaymentCreateRequest,
    user_id: Optional[uuid.UUID] = None,
) -> Payment:
    """
    Record a new payment transaction against an invoice or member.
    Enforces tenant isolation, balance validation, and optional receipt generation.
    """
    # 1. Verify member exists and belongs to tenant
    member = (
        db.query(Member)
        .filter(Member.id == payload.member_id, Member.tenant_id == tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this tenant",
        )

    invoice: Optional[Invoice] = None
    if payload.invoice_id is not None:
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == payload.invoice_id, Invoice.tenant_id == tenant_id)
            .with_for_update()
            .first()
        )
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found in this tenant",
            )
        if invoice.member_id != payload.member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice does not belong to the specified member",
            )
        if invoice.invoice_status == InvoiceStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot record payment against a cancelled invoice",
            )
        if invoice.invoice_status == InvoiceStatus.PAID or invoice.balance_amount_paise <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is already fully paid",
            )
        if payload.amount_paise > invoice.balance_amount_paise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Payment amount of ₹{payload.amount_paise / 100:.2f} exceeds "
                    f"outstanding invoice balance of ₹{invoice.balance_amount_paise / 100:.2f}"
                ),
            )

        # Update invoice balance atomically
        invoice.paid_amount_paise += payload.amount_paise
        invoice.balance_amount_paise = invoice.amount_paise - invoice.paid_amount_paise
        if invoice.balance_amount_paise == 0:
            invoice.invoice_status = InvoiceStatus.PAID
        else:
            invoice.invoice_status = InvoiceStatus.PARTIALLY_PAID
        db.add(invoice)

    payment_date = payload.payment_date or datetime.now(timezone.utc)
    payment = Payment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=payload.member_id,
        invoice_id=payload.invoice_id,
        amount_paise=payload.amount_paise,
        payment_method=payload.payment_method,
        payment_status=PaymentStatus.COMPLETED,
        transaction_reference=payload.transaction_reference,
        payment_date=payment_date,
        notes=payload.notes,
    )
    db.add(payment)
    db.flush()

    max_retries = 5
    for attempt in range(max_retries):
        receipt: Optional[Receipt] = None
        if payload.auto_generate_receipt:
            receipt_number = _generate_receipt_number(db, tenant_id)
            receipt = Receipt(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                payment_id=payment.id,
                receipt_number=receipt_number,
                issued_at=datetime.now(timezone.utc),
                notes=f"Auto-generated receipt for {payment.payment_method} payment",
            )
            db.add(receipt)

        try:
            db.commit()
            db.refresh(payment)
            return payment
        except IntegrityError:
            db.rollback()
            # If rolling back, re-add payment and invoice updates for retry
            if invoice is not None:
                db.add(invoice)
            db.add(payment)
            db.flush()
            if attempt == max_retries - 1:
                raise


def get_payment(
    db: Session,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    for_update: bool = False,
) -> Payment:
    """Retrieve payment by ID strictly scoped to tenant, with optional row lock."""
    query = db.query(Payment).filter(Payment.id == payment_id, Payment.tenant_id == tenant_id)
    if for_update:
        query = query.with_for_update()
    payment = query.first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


def list_payments(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: Optional[uuid.UUID] = None,
    invoice_id: Optional[uuid.UUID] = None,
    payment_method: Optional[PaymentMethod] = None,
    payment_status: Optional[PaymentStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> PaymentListResponse:
    """List paginated payments with optional filters."""
    query = db.query(Payment).filter(Payment.tenant_id == tenant_id)

    if member_id is not None:
        query = query.filter(Payment.member_id == member_id)
    if invoice_id is not None:
        query = query.filter(Payment.invoice_id == invoice_id)
    if payment_method is not None:
        query = query.filter(Payment.payment_method == payment_method)
    if payment_status is not None:
        query = query.filter(Payment.payment_status == payment_status)
    if from_date is not None:
        start_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        query = query.filter(Payment.payment_date >= start_dt)
    if to_date is not None:
        end_dt = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        query = query.filter(Payment.payment_date <= end_dt)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size

    payments = (
        query.order_by(Payment.payment_date.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for p in payments:
        resp = PaymentResponse.model_validate(p)
        if p.receipt:
            resp.receipt_number = p.receipt.receipt_number
            resp.receipt_id = p.receipt.id
        items.append(resp)

    return PaymentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


def refund_payment(
    db: Session,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: RefundRequest,
    initiated_by_id: Optional[uuid.UUID] = None,
) -> Refund:
    """
    Process full or partial refund for a completed payment.
    Re-adjusts linked invoice balances and preserves audit trail.
    """
    payment = get_payment(db, tenant_id, payment_id, for_update=True)

    if payment.payment_status not in (
        PaymentStatus.COMPLETED,
        PaymentStatus.PARTIALLY_REFUNDED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot refund payment with status '{payment.payment_status}'. "
                "Only COMPLETED or PARTIALLY_REFUNDED payments can be refunded."
            ),
        )

    # Calculate already refunded amount
    total_refunded = sum(
        r.amount_paise
        for r in payment.refunds
        if r.refund_type == RefundType.REFUND and r.status == RefundStatus.COMPLETED
    )
    refundable_balance = payment.amount_paise - total_refunded

    if payload.amount_paise > refundable_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Refund amount of ₹{payload.amount_paise / 100:.2f} exceeds "
                f"remaining refundable balance of ₹{refundable_balance / 100:.2f}"
            ),
        )

    refund = Refund(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        payment_id=payment.id,
        amount_paise=payload.amount_paise,
        reason=payload.reason,
        refund_type=RefundType.REFUND,
        status=RefundStatus.COMPLETED,
        transaction_reference=payload.transaction_reference,
        initiated_by_id=initiated_by_id,
    )
    db.add(refund)

    new_total_refunded = total_refunded + payload.amount_paise
    if new_total_refunded == payment.amount_paise:
        payment.payment_status = PaymentStatus.REFUNDED
    else:
        payment.payment_status = PaymentStatus.PARTIALLY_REFUNDED
    db.add(payment)

    # Re-adjust linked invoice balance
    if payment.invoice_id is not None and payment.invoice is not None:
        inv = payment.invoice
        inv.paid_amount_paise -= payload.amount_paise
        inv.balance_amount_paise = inv.amount_paise - inv.paid_amount_paise
        today = get_gym_today(db, tenant_id)
        if inv.paid_amount_paise == 0:
            inv.invoice_status = (
                InvoiceStatus.OVERDUE if inv.due_date < today else InvoiceStatus.ISSUED
            )
        else:
            inv.invoice_status = (
                InvoiceStatus.OVERDUE if inv.due_date < today else InvoiceStatus.PARTIALLY_PAID
            )
        db.add(inv)

    db.commit()
    db.refresh(refund)
    return refund


def reverse_payment(
    db: Session,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: ReversalRequest,
    initiated_by_id: Optional[uuid.UUID] = None,
) -> Refund:
    """
    Reverse a payment (e.g. bounced cheque, credit card chargeback, clerical mistake).
    Marks payment as REVERSED, creates an audit reversal record, and restores invoice balance.
    """
    payment = get_payment(db, tenant_id, payment_id, for_update=True)

    if payment.payment_status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot reverse payment with status '{payment.payment_status}'. "
                "Only COMPLETED payments without existing refunds can be reversed."
            ),
        )

    # Check that no refunds have been issued
    has_refunds = any(
        r.status == RefundStatus.COMPLETED for r in payment.refunds
    )
    if has_refunds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reverse a payment that already has refund records. Use refund instead.",
        )

    reversal = Refund(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        payment_id=payment.id,
        amount_paise=payment.amount_paise,
        reason=payload.reason,
        refund_type=RefundType.REVERSAL,
        status=RefundStatus.COMPLETED,
        transaction_reference=payload.transaction_reference,
        initiated_by_id=initiated_by_id,
    )
    db.add(reversal)

    payment.payment_status = PaymentStatus.REVERSED
    db.add(payment)

    if payment.invoice_id is not None and payment.invoice is not None:
        inv = payment.invoice
        inv.paid_amount_paise -= payment.amount_paise
        inv.balance_amount_paise = inv.amount_paise - inv.paid_amount_paise
        today = get_gym_today(db, tenant_id)
        if inv.paid_amount_paise == 0:
            inv.invoice_status = (
                InvoiceStatus.OVERDUE if inv.due_date < today else InvoiceStatus.ISSUED
            )
        else:
            inv.invoice_status = (
                InvoiceStatus.OVERDUE if inv.due_date < today else InvoiceStatus.PARTIALLY_PAID
            )
        db.add(inv)

    db.commit()
    db.refresh(reversal)
    return reversal


def generate_receipt(
    db: Session,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    notes: Optional[str] = None,
) -> Receipt:
    """Manually generate a receipt for a completed payment if not auto-generated."""
    payment = get_payment(db, tenant_id, payment_id)

    if payment.payment_status not in (
        PaymentStatus.COMPLETED,
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipts can only be generated for completed payments",
        )

    existing = (
        db.query(Receipt)
        .filter(Receipt.payment_id == payment_id, Receipt.tenant_id == tenant_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Receipt already exists for this payment (Receipt Number: {existing.receipt_number})",
        )

    max_retries = 5
    for attempt in range(max_retries):
        receipt_number = _generate_receipt_number(db, tenant_id)
        receipt = Receipt(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            payment_id=payment.id,
            receipt_number=receipt_number,
            issued_at=datetime.now(timezone.utc),
            notes=notes,
        )
        db.add(receipt)
        try:
            db.commit()
            db.refresh(receipt)
            return receipt
        except IntegrityError:
            db.rollback()
            if attempt == max_retries - 1:
                raise


def get_receipt(db: Session, tenant_id: uuid.UUID, receipt_id: uuid.UUID) -> Receipt:
    """Retrieve receipt by receipt ID strictly scoped to tenant."""
    receipt = (
        db.query(Receipt)
        .filter(Receipt.id == receipt_id, Receipt.tenant_id == tenant_id)
        .first()
    )
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found",
        )
    return receipt


def get_receipt_by_payment(db: Session, tenant_id: uuid.UUID, payment_id: uuid.UUID) -> Receipt:
    """Retrieve receipt for a specific payment strictly scoped to tenant."""
    receipt = (
        db.query(Receipt)
        .filter(Receipt.payment_id == payment_id, Receipt.tenant_id == tenant_id)
        .first()
    )
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No receipt found for this payment",
        )
    return receipt


def get_daily_summary(
    db: Session,
    tenant_id: uuid.UUID,
    target_date: Optional[date] = None,
) -> DailySummaryResponse:
    """
    Generate daily close-of-business collection summary.
    Uses tenant's configured timezone. Distinguishes gross collections,
    refunds, reversals, and net collections.
    """
    tz_str = _get_tenant_tz(db, tenant_id)
    tz = ZoneInfo(tz_str)

    if target_date is None:
        target_date = datetime.now(tz).date()

    # Time bounds in tenant's timezone converted to UTC for DB filtering
    start_local = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    # Query all payments tendered on this date (completed, partially refunded, fully refunded, or reversed)
    # Tendered gross includes all received transactions so deducting refunds/reversals produces accurate net collections.
    valid_statuses = (
        PaymentStatus.COMPLETED,
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
        PaymentStatus.REVERSED,
    )
    payments = (
        db.query(Payment)
        .filter(
            Payment.tenant_id == tenant_id,
            Payment.payment_status.in_(valid_statuses),
            Payment.payment_date >= start_utc,
            Payment.payment_date <= end_utc,
        )
        .all()
    )

    cash_paise = sum(p.amount_paise for p in payments if p.payment_method == PaymentMethod.CASH)
    upi_paise = sum(p.amount_paise for p in payments if p.payment_method == PaymentMethod.UPI)
    card_paise = sum(p.amount_paise for p in payments if p.payment_method == PaymentMethod.CARD)
    bank_paise = sum(p.amount_paise for p in payments if p.payment_method == PaymentMethod.BANK_TRANSFER)
    cheque_paise = sum(p.amount_paise for p in payments if p.payment_method == PaymentMethod.CHEQUE)

    total_gross = cash_paise + upi_paise + card_paise + bank_paise + cheque_paise
    transaction_count = len(payments)

    # Query refunds and reversals occurring on this date
    refunds = (
        db.query(Refund)
        .filter(
            Refund.tenant_id == tenant_id,
            Refund.status == RefundStatus.COMPLETED,
            Refund.created_at >= start_utc,
            Refund.created_at <= end_utc,
        )
        .all()
    )

    total_refunds = sum(r.amount_paise for r in refunds if r.refund_type == RefundType.REFUND)
    total_reversals = sum(r.amount_paise for r in refunds if r.refund_type == RefundType.REVERSAL)
    refund_count = len(refunds)

    net_collections = total_gross - total_refunds - total_reversals

    return DailySummaryResponse(
        tenant_id=tenant_id,
        date=target_date,
        total_gross_paise=total_gross,
        cash_paise=cash_paise,
        upi_paise=upi_paise,
        card_paise=card_paise,
        bank_transfer_paise=bank_paise,
        cheque_paise=cheque_paise,
        total_refunds_paise=total_refunds,
        total_reversals_paise=total_reversals,
        net_collections_paise=net_collections,
        transaction_count=transaction_count,
        refund_count=refund_count,
    )

