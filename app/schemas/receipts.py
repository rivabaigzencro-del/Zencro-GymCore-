"""Pydantic schemas for Receipts."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ReceiptCreateRequest(BaseModel):
    """Payload to manually generate a receipt for a completed payment."""
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes on receipt")


class ReceiptResponse(BaseModel):
    """Payment receipt details returned by the API."""
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    receipt_number: str
    issued_at: datetime
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Associated payment snapshot fields (optional convenience)
    amount_paise: Optional[int] = None
    payment_method: Optional[str] = None
    member_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

