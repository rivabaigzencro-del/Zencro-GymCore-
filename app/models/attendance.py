"""Attendance model — member check-in/check-out and attendance tracking strictly scoped to Tenant."""
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
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.member import Member
    from app.models.user import User


class CheckInMethod(str, enum.Enum):
    """Method used for gym check-in."""
    MANUAL = "MANUAL"
    QR = "QR"


class Attendance(Base):
    """
    Attendance record tracking gym facility check-ins and check-outs.
    Scoped strictly to Tenant and Member.
    Supports manual check-ins (by staff) and self/kiosk QR code validation.
    Enforces that check-out cannot precede check-in and prevents concurrent duplicate active check-ins.
    """
    __tablename__ = "attendance"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique attendance record UUID identifier",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant gym facility identifier enforcing multi-tenant isolation",
    )
    member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated gym member",
    )
    check_in_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="UTC timestamp when member checked in",
    )
    check_out_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="UTC timestamp when member checked out (null if currently active in gym)",
    )
    check_in_method = Column(
        SQLEnum(CheckInMethod, name="check_in_method", native_enum=True),
        nullable=False,
        default=CheckInMethod.MANUAL,
        doc="Check-in method used (MANUAL or QR)",
    )
    checked_in_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Staff member who processed the check-in (null for self QR)",
    )
    checked_out_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Staff member who processed the check-out",
    )
    is_override = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Flag indicating if check-in was granted as an authorized override",
    )
    override_reason = Column(
        String(500),
        nullable=True,
        doc="Mandatory audit reason if check-in was an override",
    )
    override_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Staff user (OWNER/MANAGER) who approved the override",
    )

    # Timestamps
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
        back_populates="attendance_records",
        foreign_keys=[tenant_id],
        doc="Associated gym facility tenant",
    )
    member = relationship(
        "Member",
        back_populates="attendance_records",
        foreign_keys=[member_id],
        doc="Associated gym member",
    )
    checked_in_by = relationship(
        "User",
        foreign_keys=[checked_in_by_id],
        doc="Staff user who processed the check-in",
    )
    checked_out_by = relationship(
        "User",
        foreign_keys=[checked_out_by_id],
        doc="Staff user who processed the check-out",
    )
    override_by = relationship(
        "User",
        foreign_keys=[override_by_id],
        doc="Staff user who approved the override",
    )

    __table_args__ = (
        CheckConstraint(
            "(check_out_time IS NULL) OR (check_out_time >= check_in_time)",
            name="chk_attendance_checkout_after_checkin",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_attendance_id_tenant"),
        ForeignKeyConstraint(
            ["member_id", "tenant_id"],
            ["members.id", "members.tenant_id"],
            ondelete="CASCADE",
            name="fk_attendance_member_tenant",
        ),
        # Partial index for active check-ins (PostgreSQL)
        Index(
            "ix_attendance_active_member",
            "member_id",
            unique=True,
            sqlite_where=text("check_out_time IS NULL"),
            postgresql_where=text("check_out_time IS NULL"),
        ),
    )

    @property
    def is_active(self) -> bool:
        """Returns True if member is currently checked in and has not checked out."""
        return self.check_out_time is None

    @property
    def duration_minutes(self) -> int | None:
        """Returns visit duration in minutes if checked out, else None."""
        if self.check_out_time and self.check_in_time:
            delta = self.check_out_time - self.check_in_time
            return max(0, int(delta.total_seconds() / 60))
        return None

    def __repr__(self) -> str:
        return (
            f"<Attendance id={self.id} member_id={self.member_id} "
            f"check_in={self.check_in_time} check_out={self.check_out_time} method={self.check_in_method}>"
        )

