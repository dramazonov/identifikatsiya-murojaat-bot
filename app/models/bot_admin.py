from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BotAdmin(Base):
    """Dynamically managed bot administrator.

    ROOT superadmins configured through SUPERADMIN_IDS stay outside this table
    and therefore cannot be removed from inside Telegram. Rows here are the
    admins/superadmins that a superadmin adds from the bot panel.
    """

    __tablename__ = "bot_admins"
    __table_args__ = (
        UniqueConstraint("telegram_id", name="uq_bot_admins_telegram_id"),
        CheckConstraint("role IN ('SUPERADMIN', 'ADMIN')", name="ck_bot_admins_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
