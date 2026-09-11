from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_for_language = State()
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_district = State()
    waiting_for_appeal = State()


class AppealSubmissionStates(StatesGroup):
    """Citizen-side Stage 22 appeal submission workflow."""

    waiting_for_category = State()
    waiting_for_text = State()
    waiting_for_attachment = State()
    waiting_for_confirmation = State()


class SuggestionStates(StatesGroup):
    waiting_for_suggestion = State()


class AccountSettings(StatesGroup):
    """Citizen account/settings states."""

    waiting_for_phone = State()


class AdminStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_search = State()
    waiting_for_admin_id = State()
    waiting_for_admin_role = State()


class AdminContactStates(StatesGroup):
    """User-side state for "👨‍💼 Админ билан боғланиш" (composing the message)."""

    waiting_for_message = State()


class AdminContactReplyStates(StatesGroup):
    """Admin-side state for replying to an admin-contact message.

    Kept separate from AdminStates.waiting_for_reply (used for appeal
    replies) so the two reply flows never get mixed up.
    """

    waiting_for_reply = State()
