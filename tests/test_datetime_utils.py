"""Unit tests for app.services.datetime_utils.

Run with:  py -m unittest tests.test_datetime_utils -v
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.services.datetime_utils import format_tashkent, to_tashkent, utcnow


class ToTashkentTests(unittest.TestCase):
    def test_naive_utc_is_treated_as_utc_and_shifted_by_5_hours(self) -> None:
        # This is the exact bug report scenario: a value stored as naive UTC
        # (as everything in this DB is) must come back as UTC+5 wall-clock time.
        stored_utc = datetime(2026, 9, 10, 9, 16, 0)  # naive, as read back from the DB

        tashkent = to_tashkent(stored_utc)

        self.assertEqual(tashkent.hour, 14)
        self.assertEqual(tashkent.minute, 16)
        self.assertEqual(tashkent.day, 10)

    def test_aware_utc_datetime_is_also_converted(self) -> None:
        stored_utc = datetime(2026, 9, 10, 9, 16, 0, tzinfo=timezone.utc)

        tashkent = to_tashkent(stored_utc)

        self.assertEqual(tashkent.hour, 14)
        self.assertEqual(tashkent.minute, 16)

    def test_does_not_mutate_input(self) -> None:
        stored_utc = datetime(2026, 9, 10, 9, 16, 0)

        to_tashkent(stored_utc)

        self.assertIsNone(stored_utc.tzinfo)
        self.assertEqual(stored_utc.hour, 9)

    def test_midnight_rollover_into_next_day(self) -> None:
        # 20:16 UTC + 5h crosses midnight -> next day 01:16 Tashkent time.
        stored_utc = datetime(2026, 9, 10, 20, 16, 0)

        tashkent = to_tashkent(stored_utc)

        self.assertEqual(tashkent.day, 11)
        self.assertEqual(tashkent.hour, 1)
        self.assertEqual(tashkent.minute, 16)

    def test_tashkent_has_no_dst_fixed_utc_plus_5(self) -> None:
        winter = to_tashkent(datetime(2026, 1, 10, 9, 16, 0))
        summer = to_tashkent(datetime(2026, 7, 10, 9, 16, 0))

        self.assertEqual(winter.utcoffset().total_seconds(), 5 * 3600)
        self.assertEqual(summer.utcoffset().total_seconds(), 5 * 3600)


class FormatTashkentTests(unittest.TestCase):
    def test_default_format_matches_admin_notification_format(self) -> None:
        stored_utc = datetime(2026, 9, 10, 9, 16, 0)

        self.assertEqual(format_tashkent(stored_utc), "10.09.2026 14:16")

    def test_custom_format_is_honored(self) -> None:
        stored_utc = datetime(2026, 9, 10, 9, 16, 0)

        self.assertEqual(format_tashkent(stored_utc, "%Y-%m-%d"), "2026-09-10")


class UtcnowTests(unittest.TestCase):
    def test_returns_naive_datetime(self) -> None:
        self.assertIsNone(utcnow().tzinfo)

    def test_is_close_to_actual_utc_time(self) -> None:
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        value = utcnow()
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        self.assertLessEqual(before, value)
        self.assertLessEqual(value, after)


if __name__ == "__main__":
    unittest.main()
