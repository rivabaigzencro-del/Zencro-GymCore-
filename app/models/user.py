import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UUID,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    """Staff user roles permitted within a GymCore tenant."""
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    FRONT_DESK = "FRONT_DESK"


class User(Base):
    """
    User/Staff entity scoped strictly to a specific Tenant.
    Enforces multi-tenant isolation via tenant_id foreign key.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique user UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym facility identifier enforcing multi-tenant isolation",
    )
    name = Column(
        String(255),
        nullable=False,
        doc="Full name of staff member",
    )
    email = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Login email address",
    )
    phone = Column(
        String(50),
        nullable=True,
        doc="Contact phone number",
    )
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Securely hashed password (bcrypt / argon2)",
    )
    role = Column(
        SQLEnum(UserRole, name="user_role", native_enum=True),
        nullable=False,
        default=UserRole.FRONT_DESK,
        doc="Role determining system authorization level (OWNER, MANAGER, FRONT_DESK)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Flag indicating whether account is currently active",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        doc="UTC creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="UTC last update timestamp",
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        back_populates="users",
        doc="Associated gym facility tenant",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="AuditLog.user_id",
        doc="Audit log entries performed by this staff member",
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}' tenant_id={self.tenant_id}>"
