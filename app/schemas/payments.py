"""Pydantic schemas for Payments, Refunds, Reversals, and Financial Summaries."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.payment import PaymentMethod, PaymentStatus
from app.models.refund import RefundType, RefundStatus


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    """Payload to record a new payment transaction."""
    member_id: UUID = Field(..., description="Target gym member UUID")
    invoice_id: Optional[UUID] = Field(None, description="Optional invoice UUID to apply payment against")
    amount_paise: int = Field(
        ...,
        gt=0,
        le=10_000_000_00,  # Max ₹10,000,000 (10 crore paise)
        description="Payment amount in integer paise (₹1 = 100 paise)",
    )
    payment_method: PaymentMethod = Field(..., description="Payment method: CASH, UPI, CARD, BANK_TRANSFER, CHEQUE")
    transaction_reference: Optional[str] = Field(
        None,
        max_length=100,
        description="External transaction reference (UPI txn id, cheque no, etc.)",
    )
    payment_date: Optional[datetime] = Field(
        None,
        description="Timestamp of payment (defaults to current UTC time if not supplied)",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Staff comments or remarks")
    auto_generate_receipt: bool = Field(True, description="Whether to automatically generate a receipt")

    @field_validator("transaction_reference", "notes")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class RefundRequest(BaseModel):
    """Payload to request a full or partial refund on a completed payment."""
    amount_paise: int = Field(
        ...,
        gt=0,
        le=10_000_000_00,
        description="Amount to refund in integer paise (must be <= refundable amount)",
    )
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory audit reason for refund")
    transaction_reference: Optional[str] = Field(None, max_length=100, description="External payout reference")

    @field_validator("reason", "transaction_reference")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class ReversalRequest(BaseModel):
    """Payload to reverse a completed payment (e.g. bounced cheque, disputed charge)."""
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory audit reason for reversal")
    transaction_reference: Optional[str] = Field(None, max_length=100, description="Reversal reference or notice number")

    @field_validator("reason", "transaction_reference")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class PaymentResponse(BaseModel):
    """Payment transaction details returned by the API."""
    id: UUID
    tenant_id: UUID
    member_id: UUID
    invoice_id: Optional[UUID] = None
    amount_paise: int
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_reference: Optional[str] = None
    payment_date: datetime
    notes: Optional[str] = None
    receipt_number: Optional[str] = None
    receipt_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    """Paginated list of payments."""
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RefundResponse(BaseModel):
    """Refund or reversal transaction record returned by the API."""
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount_paise: int
    reason: str
    refund_type: RefundType
    status: RefundStatus
    transaction_reference: Optional[str] = None
    initiated_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailySummaryResponse(BaseModel):
    """Daily collection summary for close-of-business reporting."""
    tenant_id: UUID
    date: date
    total_gross_paise: int
    cash_paise: int
    upi_paise: int
    card_paise: int
    bank_transfer_paise: int
    cheque_paise: int
    total_refunds_paise: int
    total_reversals_paise: int
    net_collections_paise: int
    transaction_count: int
    refund_count: int

