"""Transient numbers that fit the existing VARCHAR(20) business-number columns."""

import secrets


def generate_temporary_number() -> str:
    """Return exactly 20 ASCII characters: TMP- plus 96 random bits.

    Twelve random bytes encode to sixteen URL-safe base64 characters without
    padding. No truncation of a UUID or schema migration is needed. Final
    numbers use different prefixes and replace this value before commit.

    Randomness is not a mathematical uniqueness guarantee. The database UNIQUE
    index is authoritative; a collision fails and rolls back the transaction
    rather than creating a duplicate. Even among a million generated values,
    the birthday collision bound is approximately 6.3e-18. In practice only
    simultaneous temporary values in the same table can conflict.
    """
    return "TMP-" + secrets.token_urlsafe(12)
