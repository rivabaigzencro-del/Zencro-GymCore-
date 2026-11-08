"""Audit Logging Service for GYMCORE.

Provides centralized, append-only audit trail logging and queries.
Enforces data sanitization so passwords, tokens, and secrets are never persisted in plain text.
"""
import math
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

SENSITIVE_KEY_PATTERNS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "authorization",
    "hashed_password",
    "new_password",
    "old_password",
    "api_key",
}


def sanitize_payload(data: Any) -> Any:
    """Recursively sanitize dict/list objects by redacting sensitive keys

    and converting non-JSON types (UUID, datetime, Decimal, Enum) to safe primitives.
    """
    if data is None:
        return None
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
                cleaned[str(k)] = "[REDACTED]"
            else:
                cleaned[str(k)] = sanitize_payload(v)
        return cleaned
    if isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    if isinstance(data, UUID):
        return str(data)
    if isinstance(data, (datetime, date, time)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, Enum):
        return data.value
    return data


def extract_client_info(request: Optional[Request]) -> Tuple[Optional[str], Optional[str]]:
    """Extract client IP address and truncated User-Agent header from FastAPI Request."""
    if not request:
        return None, None

    # Forwarded-For support if reverse proxy is present
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = None

    if ip and len(ip) > 50:
        ip = ip[:50]

    ua = request.headers.get("user-agent")
    if ua and len(ua) > 255:
        ua = ua[:255]

    return ip, ua


def log_audit_event(
    db: Session,
    tenant_id: UUID,
    action: str,
    resource_type: str,
    user_id: Optional[UUID] = None,
    resource_id: Optional[str] = None,
    before_values: Optional[Dict[str, Any]] = None,
    after_values: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Create an append-only audit log entry within the active db transaction.

    Automatically sanitizes before_values and after_values.
    Does NOT issue an isolated commit, allowing atomic commit with the calling business logic.
    """
    if request:
        req_ip, req_ua = extract_client_info(request)
        if not ip_address:
            ip_address = req_ip
        if not user_agent:
            user_agent = req_ua

    clean_before = sanitize_payload(before_values) if before_values else None
    clean_after = sanitize_payload(after_values) if after_values else None

    audit_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        before_values=clean_before,
        after_values=clean_after,
        reason=reason.strip() if reason and reason.strip() else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_entry)
    db.flush()  # Populates ID and created_at without ending transaction
    return audit_entry


def list_audit_logs(
    db: Session,
    tenant_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Retrieve paginated, strictly tenant-isolated audit log entries with optional filters."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = (
        db.query(AuditLog, User.name.label("actor_name"))
        .outerjoin(User, AuditLog.user_id == User.id)
        .filter(AuditLog.tenant_id == tenant_id)
    )

    if start_date:
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        query = query.filter(AuditLog.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
        query = query.filter(AuditLog.created_at <= end_dt)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action.strip())
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type.strip())
    if resource_id:
        query = query.filter(AuditLog.resource_id == str(resource_id).strip())

    total = query.count()
    pages = math.ceil(total / page_size) if total > 0 else 1

    records = (
        query.order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for log, actor_name in records:
        items.append({
            "id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "actor_name": actor_name or "System",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "before_values": log.before_values,
            "after_values": log.after_values,
            "reason": log.reason,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def get_audit_log_or_404(
    db: Session,
    tenant_id: UUID,
    audit_log_id: UUID,
) -> Dict[str, Any]:
    """Retrieve a single audit log entry ensuring strict tenant isolation."""
    result = (
        db.query(AuditLog, User.name.label("actor_name"))
        .outerjoin(User, AuditLog.user_id == User.id)
        .filter(AuditLog.id == audit_log_id, AuditLog.tenant_id == tenant_id)
        .first()
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {audit_log_id} not found",
        )

    log, actor_name = result
    return {
        "id": log.id,
        "tenant_id": log.tenant_id,
        "user_id": log.user_id,
        "actor_name": actor_name or "System",
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "before_values": log.before_values,
        "after_values": log.after_values,
        "reason": log.reason,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at,
    }

