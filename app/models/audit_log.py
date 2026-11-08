"""AuditLog model — immutable append-only event trail for security, governance, and audit compliance."""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UUID,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class AuditLog(Base):
    """
    Append-only audit log entry recording critical business operations.
    Enforces multi-tenant isolation via tenant_id.
    Captures actor, action type, target resource, before/after states, and reasons.
    """
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique audit log entry UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym facility identifier enforcing multi-tenant isolation",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Actor/Staff user UUID who performed the operation (null if system)",
    )
    action = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Action identifier (e.g. STAFF_CREATE, MEMBER_STATUS_CHANGE, PAYMENT_REFUND)",
    )
    resource_type = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Entity type affected (e.g. STAFF, MEMBER, MEMBERSHIP, PAYMENT, INVOICE, ATTENDANCE, SETTINGS)",
    )
    resource_id = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Identifier of the target entity (UUID string or reference code)",
    )
    before_values = Column(
        JSON,
        nullable=True,
        doc="Sanitized JSON state before modification (null for create events)",
    )
    after_values = Column(
        JSON,
        nullable=True,
        doc="Sanitized JSON state after modification",
    )
    reason = Column(
        Text,
        nullable=True,
        doc="Audit justification or override reason provided by the actor",
    )
    ip_address = Column(
        String(50),
        nullable=True,
        doc="Client IP address where request originated",
    )
    user_agent = Column(
        String(255),
        nullable=True,
        doc="Client User-Agent header snippet",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="UTC timestamp when audit entry was recorded",
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        back_populates="audit_logs",
        doc="Associated gym tenant",
    )
    user = relationship(
        "User",
        back_populates="audit_logs",
        doc="Associated actor user",
    )

    __table_args__ = (
        Index("idx_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("idx_audit_logs_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        Index("idx_audit_logs_tenant_user", "tenant_id", "user_id"),
        Index("idx_audit_logs_tenant_action", "tenant_id", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action='{self.action}' resource='{self.resource_type}:{self.resource_id}' tenant_id={self.tenant_id}>"

