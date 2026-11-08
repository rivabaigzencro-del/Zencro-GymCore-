"""Pydantic schemas for Audit Logs (Append-Only Trail)."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Read-only safe representation of an audit event."""
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    before_values: Optional[Dict[str, Any]] = None
    after_values: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated list of audit events."""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int

