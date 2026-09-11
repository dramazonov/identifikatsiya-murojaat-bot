from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

DELIVERY_DELIVERED = "DELIVERED"
DELIVERY_FAILED = "FAILED"


def classify_delivery_exception(exc: Exception) -> tuple[str, bool]:
    """Return a sanitized error code and whether the user is unreachable.

    Only the exception class name is persisted. Raw Telegram exception text is
    intentionally not stored because it can contain request details.
    """
    unreachable = isinstance(exc, TelegramForbiddenError)
    if isinstance(exc, TelegramBadRequest):
        message = str(exc).lower()
        unreachable = unreachable or any(
            marker in message
            for marker in ("chat not found", "user is deactivated", "bot was blocked")
        )
    return type(exc).__name__[:64], unreachable
