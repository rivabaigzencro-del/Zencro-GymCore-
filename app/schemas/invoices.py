"""Pydantic schemas for Invoices and billing management."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from app.models.invoice import InvoiceStatus


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class InvoiceCreateRequest(BaseModel):
    """Payload to create a new billing invoice."""
    member_id: UUID = Field(..., description="Target gym member UUID")
    membership_id: Optional[UUID] = Field(None, description="Optional linked membership UUID")
    amount_paise: int = Field(
        ...,
        gt=0,
        le=10_000_000_00,  # Max ₹10,000,000 (10 crore paise)
        description="Invoice total amount in integer paise (₹1 = 100 paise)",
    )
    issue_date: Optional[date] = Field(
        None,
        description="Invoice issue date (defaults to gym's current business date)",
    )
    due_date: Optional[date] = Field(
        None,
        description="Payment due date (defaults to issue date if not specified)",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Billing description or fee summary",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @model_validator(mode="after")
    def validate_dates(self) -> "InvoiceCreateRequest":
        if self.issue_date is not None and self.due_date is not None:
            if self.due_date < self.issue_date:
                raise ValueError("due_date cannot be earlier than issue_date")
        return self


class InvoiceUpdateRequest(BaseModel):
    """Payload to update permitted fields of an existing invoice."""
    due_date: Optional[date] = Field(None, description="Updated payment due date")
    description: Optional[str] = Field(None, max_length=500, description="Updated description")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class InvoiceCancelRequest(BaseModel):
    """Payload to cancel an unpaid invoice."""
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class InvoiceResponse(BaseModel):
    """Invoice entity details returned by the API."""
    id: UUID
    tenant_id: UUID
    member_id: UUID
    membership_id: Optional[UUID] = None
    invoice_number: str
    amount_paise: int
    paid_amount_paise: int
    balance_amount_paise: int
    invoice_status: InvoiceStatus
    issue_date: date
    due_date: date
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OutstandingDuesResponse(BaseModel):
    """Summary of outstanding dues across tenant or for a specific member."""
    tenant_id: UUID
    member_id: Optional[UUID] = None
    total_invoiced_paise: int
    total_paid_paise: int
    total_outstanding_paise: int
    overdue_invoices_count: int
    overdue_amount_paise: int

