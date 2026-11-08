"""Invoice service — business logic for invoice generation, balances, and dues tracking."""
import math
import uuid
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.member import Member
from app.models.membership import Membership
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoices import (
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
    InvoiceCancelRequest,
    InvoiceListResponse,
    OutstandingDuesResponse,
)
from app.services.audit_service import log_audit_event


def get_gym_today(db: Optional[Session] = None, tenant_id: Optional[uuid.UUID] = None) -> date:
    """Return today's date in tenant's timezone (defaults to Asia/Kolkata)."""
    tz_name = "Asia/Kolkata"
    if db is not None and tenant_id is not None:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.timezone:
            tz_name = tenant.timezone
    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return date.today()


def _generate_invoice_number(db: Session, tenant_id: uuid.UUID) -> str:
    """
    Generate a sequentially unique invoice number for the tenant.
    Format: INV-{YYYYMM}-{seq:04d}
    Queries highest existing sequence number with this prefix to prevent collision.
    """
    today = get_gym_today(db, tenant_id)
    prefix = f"INV-{today.strftime('%Y%m')}-"

    last_record = (
        db.query(Invoice.invoice_number)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number.like(f"{prefix}%"),
        )
        .order_by(Invoice.invoice_number.desc())
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
            db.query(Invoice.id)
            .filter(Invoice.tenant_id == tenant_id, Invoice.invoice_number == candidate)
            .first()
        )
        if not exists:
            return candidate
        seq += 1


def _check_and_update_overdue(db: Session, invoice: Invoice, today: date) -> None:
    """Update invoice status to OVERDUE if due_date has passed and status is not PAID/CANCELLED."""
    if invoice.due_date < today and invoice.invoice_status in (
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
    ):
        invoice.invoice_status = InvoiceStatus.OVERDUE
        db.add(invoice)


def create_invoice(
    db: Session,
    tenant_id: uuid.UUID,
    payload: InvoiceCreateRequest,
    user_id: Optional[uuid.UUID] = None,
) -> Invoice:
    """Create a new billing invoice strictly isolated to the authenticated tenant."""
    # 1. Verify member belongs to tenant
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

    # 2. Verify optional membership belongs to tenant and member
    if payload.membership_id is not None:
        membership = (
            db.query(Membership)
            .filter(
                Membership.id == payload.membership_id,
                Membership.tenant_id == tenant_id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership not found in this tenant",
            )
        if membership.member_id != payload.member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Membership does not belong to the specified member",
            )

    today = get_gym_today(db, tenant_id)
    issue_date = payload.issue_date or today
    due_date = payload.due_date or issue_date

    if due_date < issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="due_date cannot be earlier than issue_date",
        )

    # Determine initial status
    initial_status = InvoiceStatus.ISSUED
    if due_date < today:
        initial_status = InvoiceStatus.OVERDUE

    max_retries = 5
    for attempt in range(max_retries):
        invoice_number = _generate_invoice_number(db, tenant_id)
        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            member_id=payload.member_id,
            membership_id=payload.membership_id,
            invoice_number=invoice_number,
            amount_paise=payload.amount_paise,
            paid_amount_paise=0,
            balance_amount_paise=payload.amount_paise,
            invoice_status=initial_status,
            issue_date=issue_date,
            due_date=due_date,
            description=payload.description,
        )

        db.add(invoice)

        log_audit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action="INVOICE_CREATE",
            resource_type="INVOICE",
            resource_id=str(invoice.id),
            after_values={
                "invoice_number": invoice.invoice_number,
                "amount_paise": invoice.amount_paise,
                "member_id": str(invoice.member_id),
                "invoice_status": invoice.invoice_status.value,
            },
            reason="Invoice created",
        )

        try:
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError:
            db.rollback()
            if attempt == max_retries - 1:
                raise


def get_invoice(db: Session, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    """Retrieve an invoice by ID strictly scoped to tenant."""
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    today = get_gym_today(db, tenant_id)
    _check_and_update_overdue(db, invoice, today)
    db.commit()
    db.refresh(invoice)
    return invoice


def list_invoices(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: Optional[uuid.UUID] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> InvoiceListResponse:
    """List paginated invoices with optional filters."""
    query = db.query(Invoice).filter(Invoice.tenant_id == tenant_id)

    if member_id is not None:
        query = query.filter(Invoice.member_id == member_id)
    if invoice_status is not None:
        query = query.filter(Invoice.invoice_status == invoice_status)
    if from_date is not None:
        query = query.filter(Invoice.issue_date >= from_date)
    if to_date is not None:
        query = query.filter(Invoice.issue_date <= to_date)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size

    invoices = (
        query.order_by(Invoice.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    today = get_gym_today(db, tenant_id)
    for inv in invoices:
        _check_and_update_overdue(db, inv, today)
    db.commit()

    return InvoiceListResponse(
        items=invoices,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


def update_invoice(
    db: Session,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payload: InvoiceUpdateRequest,
) -> Invoice:
    """Update permitted fields (due_date, description) of an invoice."""
    invoice = get_invoice(db, tenant_id, invoice_id)

    if invoice.invoice_status == InvoiceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a cancelled invoice",
        )

    if payload.due_date is not None:
        if payload.due_date < invoice.issue_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="due_date cannot precede issue_date",
            )
        invoice.due_date = payload.due_date
        today = get_gym_today(db, tenant_id)
        _check_and_update_overdue(db, invoice, today)

    if payload.description is not None:
        invoice.description = payload.description

    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel_invoice(
    db: Session,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payload: Optional[InvoiceCancelRequest] = None,
    user_id: Optional[uuid.UUID] = None,
) -> Invoice:
    """Cancel an invoice that has no outstanding paid amount."""
    invoice = get_invoice(db, tenant_id, invoice_id)

    if invoice.invoice_status == InvoiceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already cancelled",
        )

    if invoice.paid_amount_paise > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot cancel invoice with paid amount of ₹{invoice.paid_amount_paise / 100:.2f}. "
                "Refund or reverse all payments first."
            ),
        )

    before_status = invoice.invoice_status.value
    invoice.invoice_status = InvoiceStatus.CANCELLED
    if payload and payload.reason:
        desc = f"{invoice.description or ''} [Cancelled: {payload.reason}]".strip()
        invoice.description = desc[:500]

    db.add(invoice)

    log_audit_event(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="INVOICE_CANCEL",
        resource_type="INVOICE",
        resource_id=str(invoice.id),
        before_values={"invoice_status": before_status},
        after_values={"invoice_status": InvoiceStatus.CANCELLED.value},
        reason=payload.reason if payload else "Invoice cancelled",
    )

    db.commit()
    db.refresh(invoice)
    return invoice


def get_outstanding_dues(
    db: Session,
    tenant_id: uuid.UUID,
    member_id: Optional[uuid.UUID] = None,
) -> OutstandingDuesResponse:
    """Calculate outstanding financial dues for the tenant or a specific member."""
    query = db.query(Invoice).filter(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_status != InvoiceStatus.CANCELLED,
    )
    if member_id is not None:
        query = query.filter(Invoice.member_id == member_id)

    invoices = query.all()
    today = get_gym_today(db, tenant_id)

    total_invoiced = sum(i.amount_paise for i in invoices)
    total_paid = sum(i.paid_amount_paise for i in invoices)
    total_outstanding = sum(i.balance_amount_paise for i in invoices)

    overdue_invoices = [
        i for i in invoices if i.due_date < today and i.balance_amount_paise > 0
    ]
    overdue_count = len(overdue_invoices)
    overdue_amount = sum(i.balance_amount_paise for i in overdue_invoices)

    return OutstandingDuesResponse(
        tenant_id=tenant_id,
        member_id=member_id,
        total_invoiced_paise=total_invoiced,
        total_paid_paise=total_paid,
        total_outstanding_paise=total_outstanding,
        overdue_invoices_count=overdue_count,
        overdue_amount_paise=overdue_amount,
    )

