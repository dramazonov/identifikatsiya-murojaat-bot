from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Appeal(Base):
    __tablename__ = "appeals"
    # Keeps SQLite from ever reusing a deleted row's id, so appeal numbers
    # (derived from this id, see app/services/appeal_service.py) stay unique
    # and strictly sequential even across deletions.
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appeal_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    appeal_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Set once an admin starts handling the appeal (IN_PROGRESS) / answers it
    # (COMPLETED). Stores the admin's Telegram user id (from ADMIN_IDS), not a
    # foreign key into `users` -- admins are not registered citizens.
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Plain (non-Mapped-annotated) relationship() to avoid needing a forward-ref
    # import of User here; the string "User" is resolved via the shared registry.
    user = relationship("User", back_populates="appeals")
