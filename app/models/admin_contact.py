from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AdminContact(Base):
    __tablename__ = "admin_contacts"
    # Keeps SQLite from ever reusing a deleted row's id, so contact numbers
    # (derived from this id, see app/services/admin_contact_service.py) stay
    # unique and strictly sequential even across deletions -- same rationale
    # as Appeal/Suggestion.
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contact_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Nullable: a citizen can use "👨‍💼 Админ билан боғланиш" without going
    # through the mandatory registration flow. In practice
    # app.services.admin_contact_service.create_admin_contact always creates
    # (or reuses) a minimal `users` row to retain the sender's telegram_id --
    # needed to deliver the admin's reply -- but the column itself stays
    # nullable to allow for a contact record with no resolvable user.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Set once an admin starts handling the contact (IN_PROGRESS) / answers it
    # (COMPLETED). Stores the admin's Telegram user id (from ADMIN_IDS), not a
    # foreign key into `users` -- admins are not registered citizens.
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Plain (non-Mapped-annotated) relationship() to avoid needing a forward-ref
    # import of User here; the string "User" is resolved via the shared registry.
    user = relationship("User", back_populates="admin_contacts")
