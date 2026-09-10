from __future__ import annotations

"""Single source of truth for datetime handling across the bot.

Storage strategy
-----------------
Every timestamp in the database (``users.created_at``/``updated_at``,
``appeals.created_at``/``updated_at``/``answered_at``,
``suggestions.created_at``/``updated_at``) is stored as **timezone-naive
UTC**. This was already the case before this module existed -- SQLite's
``CURRENT_TIMESTAMP`` / ``func.now()`` (used as these columns'
``server_default``) is always UTC, and application code that sets a
timestamp explicitly (e.g. when creating an appeal) must use :func:`utcnow`
below so it agrees with that default. Because the strategy is "naive UTC"
regardless of which machine runs the process, a Windows dev box and a
Linux/VPS production host produce identical, comparable timestamps -- the
host's own local timezone never leaks into stored data.

Display strategy
-----------------
Uzbekistan time (Asia/Tashkent, UTC+5, no DST) is only ever produced at the
point a timestamp is shown to a human -- admin notifications, citizen
confirmations, etc. Use :func:`format_tashkent` (or :func:`to_tashkent` if
the aware datetime itself is needed rather than a formatted string) there.
Never call ``.strftime`` directly on a raw DB timestamp.

``zoneinfo.ZoneInfo`` needs an IANA tz database to resolve "Asia/Tashkent".
Linux/VPS hosts normally ship one; Windows does not, so this project depends
on the ``tzdata`` package (see requirements.txt) to make lookups behave the
same on both platforms.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

DEFAULT_DISPLAY_FORMAT = "%d.%m.%Y %H:%M"


def utcnow() -> datetime:
    """Current time as a timezone-naive UTC datetime.

    Use this everywhere the app needs to stamp a ``created_at``/
    ``updated_at``/``answered_at`` value in code (as opposed to relying on
    the DB's ``server_default=func.now()``), so every stored timestamp -- DB-
    generated or app-generated -- shares the same "naive UTC" strategy.
    Equivalent to the now-deprecated ``datetime.utcnow()``, but expressed via
    the timezone-aware API so it isn't tied to that deprecation.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_tashkent(value: datetime) -> datetime:
    """Convert a stored timestamp to an aware Asia/Tashkent datetime.

    ``value`` is treated as UTC: a naive value (as everything currently in
    this app's DB is) is first stamped as UTC, then converted; an already
    timezone-aware value is converted as-is. ``value`` itself is never
    mutated.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TASHKENT_TZ)


def format_tashkent(value: datetime, fmt: str = DEFAULT_DISPLAY_FORMAT) -> str:
    """Format a stored (UTC) timestamp for display in Asia/Tashkent time.

    Used by both appeal and suggestion notifications so the two stay
    formatted identically.
    """
    return to_tashkent(value).strftime(fmt)
