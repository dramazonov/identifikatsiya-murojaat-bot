from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            value = int(part)
            if value not in ids:
                ids.append(value)
    return ids


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
SUPERADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("SUPERADMIN_IDS", ""))

# Backward-compatible safety net: Stage 23 introduces SUPERADMIN_IDS, but an
# existing deployment may be upgraded before that variable is added in Render.
# In that case the first configured ADMIN_IDS entry acts as the temporary
# superadmin so suggestion handling is never silently disabled. Production
# should still set SUPERADMIN_IDS explicitly after deployment.
if not SUPERADMIN_IDS and ADMIN_IDS:
    SUPERADMIN_IDS = [ADMIN_IDS[0]]


def all_admin_ids() -> list[int]:
    """Every Telegram id allowed to use admin functions, without duplicates."""
    return list(dict.fromkeys([*SUPERADMIN_IDS, *ADMIN_IDS]))


def is_superadmin(telegram_id: int) -> bool:
    return telegram_id in SUPERADMIN_IDS


def is_admin(telegram_id: int) -> bool:
    return telegram_id in all_admin_ids()
