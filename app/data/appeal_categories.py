from __future__ import annotations

# Stable internal codes stored in the database. User-facing labels are always
# resolved through app.i18n, so changing wording never changes stored data.
APPEAL_CATEGORIES: tuple[str, ...] = (
    "IDENTIFICATION",
    "TAG",
    "REGISTRATION",
    "DEREGISTRATION",
    "DATABASE",
    "TECHNICAL",
    "LEGISLATION",
    "OTHER",
)


def is_valid_appeal_category(code: str | None) -> bool:
    return bool(code and code in APPEAL_CATEGORIES)
