from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """Append-only application audit trail for privileged admin actions.

    No foreign keys are used deliberately: deleting or changing an admin/user
    record must never erase historical accountability. The application exposes
    read-only audit views and no update/delete operation for this table.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('TELEGRAM', 'WEB')",
            name="ck_audit_logs_channel",
        ),
        Index("ix_audit_logs_actor_created_at", "actor_telegram_id", "created_at"),
        Index("ix_audit_logs_action_created_at", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
