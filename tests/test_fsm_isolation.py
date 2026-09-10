"""FSM multi-user isolation tests (instruction #8).

The app never implements its own FSM storage -- it relies entirely on
aiogram's ``FSMContext``/``BaseStorage``, keyed by (bot_id, chat_id,
user_id). These tests verify that key actually isolates two different users'
state and data from each other, which is what guarantees one citizen's
appeal/reply progress can never leak into or clobber another's.
"""

from __future__ import annotations

from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.states import AdminStates, Registration

BOT_ID = 12345


async def test_two_users_state_and_data_are_independent() -> None:
    storage = MemoryStorage()
    key_a = StorageKey(bot_id=BOT_ID, chat_id=1001, user_id=1001)
    key_b = StorageKey(bot_id=BOT_ID, chat_id=2002, user_id=2002)

    await storage.set_state(key_a, Registration.waiting_for_appeal)
    await storage.set_data(key_a, {"full_name": "User A", "appeal_draft": "hello"})

    await storage.set_state(key_b, Registration.waiting_for_phone)
    await storage.set_data(key_b, {"full_name": "User B"})

    assert await storage.get_state(key_a) == Registration.waiting_for_appeal.state
    assert await storage.get_data(key_a) == {"full_name": "User A", "appeal_draft": "hello"}

    assert await storage.get_state(key_b) == Registration.waiting_for_phone.state
    assert await storage.get_data(key_b) == {"full_name": "User B"}


async def test_clearing_one_users_state_does_not_touch_the_other() -> None:
    storage = MemoryStorage()
    key_a = StorageKey(bot_id=BOT_ID, chat_id=1001, user_id=1001)
    key_b = StorageKey(bot_id=BOT_ID, chat_id=2002, user_id=2002)

    await storage.set_state(key_a, Registration.waiting_for_appeal)
    await storage.set_data(key_a, {"full_name": "User A"})
    await storage.set_state(key_b, AdminStates.waiting_for_reply)
    await storage.set_data(key_b, {"appeal_id": 42})

    # e.g. the citizen finishes/cancels their flow -- state.clear() equivalent.
    await storage.set_state(key_a, None)
    await storage.set_data(key_a, {})

    assert await storage.get_state(key_a) is None
    assert await storage.get_data(key_a) == {}
    # An unrelated admin mid-reply for a completely different appeal is untouched.
    assert await storage.get_state(key_b) == AdminStates.waiting_for_reply.state
    assert await storage.get_data(key_b) == {"appeal_id": 42}


async def test_same_user_id_in_different_chats_is_isolated_by_chat_id() -> None:
    """StorageKey includes chat_id, not just user_id -- a private chat and (in
    principle) any other chat context for the same Telegram user never share
    state. This bot only ever talks to users in their private chat (chat_id
    == user_id for a DM), but the isolation is a property of the key itself.
    """
    storage = MemoryStorage()
    same_user_chat_1 = StorageKey(bot_id=BOT_ID, chat_id=1001, user_id=1001)
    same_user_chat_2 = StorageKey(bot_id=BOT_ID, chat_id=9999, user_id=1001)

    await storage.set_state(same_user_chat_1, Registration.waiting_for_appeal)
    await storage.set_state(same_user_chat_2, Registration.waiting_for_phone)

    assert await storage.get_state(same_user_chat_1) == Registration.waiting_for_appeal.state
    assert await storage.get_state(same_user_chat_2) == Registration.waiting_for_phone.state


async def test_unset_user_has_no_state_or_data() -> None:
    storage = MemoryStorage()
    key_untouched = StorageKey(bot_id=BOT_ID, chat_id=3003, user_id=3003)

    assert await storage.get_state(key_untouched) is None
    assert await storage.get_data(key_untouched) == {}
