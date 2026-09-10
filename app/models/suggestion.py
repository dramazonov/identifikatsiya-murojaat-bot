from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Suggestion(Base):
    __tablename__ = "suggestions"
    # Keeps SQLite from ever reusing a deleted row's id, so suggestion numbers
    # (derived from this id, see app/services/suggestion_service.py) stay unique
    # and strictly sequential even across deletions.
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    suggestion_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Plain (non-Mapped-annotated) relationship() to avoid needing a forward-ref
    # import of User here; the string "User" is resolved via the shared registry.
    user = relationship("User", back_populates="suggestions")
