from __future__ import annotations

import re

MIN_FULL_NAME_LENGTH = 5
MIN_APPEAL_TEXT_LENGTH = 5
MAX_APPEAL_TEXT_LENGTH = 4000
MIN_SUGGESTION_TEXT_LENGTH = 5
MAX_SUGGESTION_TEXT_LENGTH = 4000
MIN_ADMIN_CONTACT_MESSAGE_LENGTH = 2
MAX_ADMIN_CONTACT_MESSAGE_LENGTH = 4000

_NON_DIGIT_RE = re.compile(r"\D+")


def is_valid_full_name(full_name: str) -> bool:
    """Full name must not be empty and must have at least MIN_FULL_NAME_LENGTH characters."""
    return len(full_name.strip()) >= MIN_FULL_NAME_LENGTH


def is_valid_appeal_text(appeal_text: str) -> bool:
    """Appeal text must be between MIN_APPEAL_TEXT_LENGTH and MAX_APPEAL_TEXT_LENGTH characters."""
    length = len(appeal_text.strip())
    return MIN_APPEAL_TEXT_LENGTH <= length <= MAX_APPEAL_TEXT_LENGTH


def is_valid_suggestion_text(suggestion_text: str) -> bool:
    """Suggestion text must be between MIN_SUGGESTION_TEXT_LENGTH and MAX_SUGGESTION_TEXT_LENGTH characters."""
    length = len(suggestion_text.strip())
    return MIN_SUGGESTION_TEXT_LENGTH <= length <= MAX_SUGGESTION_TEXT_LENGTH


def is_valid_admin_contact_message(message_text: str) -> bool:
    """Message text must be between MIN_ and MAX_ADMIN_CONTACT_MESSAGE_LENGTH characters.

    Whitespace-only input has length 0 after stripping, so it is rejected too.
    """
    length = len(message_text.strip())
    return MIN_ADMIN_CONTACT_MESSAGE_LENGTH <= length <= MAX_ADMIN_CONTACT_MESSAGE_LENGTH


def normalize_phone(raw_phone: str) -> str | None:
    """Normalize a phone number to +998XXXXXXXXX format.

    Accepts formats such as:
        +998901234567
        998901234567
        90 123 45 67
        90-123-45-67

    Returns None if the number cannot be reasonably validated.
    """
    digits = _NON_DIGIT_RE.sub("", raw_phone or "")

    if not digits:
        return None

    if len(digits) == 12 and digits.startswith("998"):
        national = digits[3:]
    elif len(digits) == 9:
        national = digits
    else:
        return None

    if len(national) != 9 or not national.isdigit():
        return None

    return f"+998{national}"
