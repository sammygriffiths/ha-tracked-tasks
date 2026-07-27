"""Tests for pure tracked task schedule calculation."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = ROOT / "custom_components" / "tracked_tasks" / "schedule.py"
SPEC = importlib.util.spec_from_file_location("tracked_tasks_schedule", SCHEDULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
schedule = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = schedule
SPEC.loader.exec_module(schedule)

UTC = timezone.utc


@dataclass
class State:
    """Small state test double."""

    last_completed: datetime | None = None
    completed_due_at: datetime | None = None


class TestDailySchedule(unittest.TestCase):
    """Daily schedule calculations."""

    def test_daily_pending_before_due_time(self) -> None:
        now = datetime(2026, 7, 20, 8, 30, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 7, 20, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 20, 10, 0, tzinfo=UTC))
        self.assertFalse(result.due)
        self.assertFalse(result.overdue)
        self.assertEqual(result.time_remaining, timedelta(minutes=30))
        self.assertFalse(result.current_obligation_completed)

    def test_daily_due_between_due_and_overdue_times(self) -> None:
        now = datetime(2026, 7, 20, 9, 30, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "due")
        self.assertTrue(result.due)
        self.assertFalse(result.overdue)
        self.assertEqual(result.time_remaining, timedelta())

    def test_daily_overdue_at_overdue_time(self) -> None:
        now = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertFalse(result.due)
        self.assertTrue(result.overdue)
        self.assertEqual(result.time_remaining, timedelta())

    def test_daily_no_overdue_time_preserves_strict_deadline(self) -> None:
        now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.overdue_at, datetime(2026, 7, 20, 9, 0, tzinfo=UTC))
        self.assertTrue(result.overdue)
        self.assertEqual(result.time_remaining, timedelta())

    def test_daily_completed_before_due_time(self) -> None:
        now = datetime(2026, 7, 20, 8, 30, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(
                last_completed=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.current_obligation_due_at, due_at)
        self.assertEqual(result.due_at, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 21, 10, 0, tzinfo=UTC))
        self.assertTrue(result.current_obligation_completed)

    def test_daily_completed_during_due_window(self) -> None:
        now = datetime(2026, 7, 20, 9, 30, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(
                last_completed=datetime(2026, 7, 20, 9, 15, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertFalse(result.due)
        self.assertFalse(result.overdue)
        self.assertEqual(result.due_at, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))

    def test_daily_completed_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00", "overdue_time": "10:00"},
            State(
                last_completed=datetime(2026, 7, 20, 9, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))
        self.assertFalse(result.overdue)

    def test_daily_rejects_overdue_time_before_due_time(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.evaluate_schedule(
                {"type": "daily", "due_time": "20:00", "overdue_time": "19:00"},
                State(),
                datetime(2026, 7, 20, 18, 0, tzinfo=UTC),
            )

    def test_daily_due_time_uses_now_timezone(self) -> None:
        london = ZoneInfo("Europe/London")
        now = datetime(2026, 7, 20, 19, 30, tzinfo=london)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "20:00", "overdue_time": "23:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at.hour, 20)
        self.assertEqual(result.due_at.tzinfo, london)
        self.assertEqual(result.due_at.utcoffset(), timedelta(hours=1))


class TestWeeklySchedule(unittest.TestCase):
    """Weekly schedule calculations."""

    def test_weekly_pending_before_due_day(self) -> None:
        now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)  # Monday

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 7, 23, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 23, 12, 0, tzinfo=UTC))
        self.assertEqual(result.time_remaining, timedelta(days=3, hours=1))

    def test_weekly_due_between_due_and_overdue_times(self) -> None:
        now = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)  # Thursday

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "due")
        self.assertTrue(result.due)
        self.assertFalse(result.overdue)

    def test_weekly_overdue_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)  # Thursday

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.due_at, datetime(2026, 7, 23, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 23, 12, 0, tzinfo=UTC))
        self.assertTrue(result.overdue)

    def test_weekly_completed_before_due_time(self) -> None:
        now = datetime(2026, 7, 22, 19, 0, tzinfo=UTC)  # Wednesday
        due_at = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(
                last_completed=datetime(2026, 7, 22, 18, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 7, 30, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 30, 12, 0, tzinfo=UTC))

    def test_weekly_completed_during_due_window(self) -> None:
        now = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)  # Thursday
        due_at = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(
                last_completed=datetime(2026, 7, 23, 9, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertFalse(result.due)
        self.assertFalse(result.overdue)
        self.assertEqual(result.due_at, datetime(2026, 7, 30, 9, 0, tzinfo=UTC))

    def test_weekly_completed_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)  # Friday
        due_at = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "weekly",
                "weekday": "thursday",
                "due_time": "09:00",
                "overdue_time": "12:00",
            },
            State(
                last_completed=datetime(2026, 7, 23, 12, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 7, 30, 9, 0, tzinfo=UTC))
        self.assertFalse(result.overdue)

    def test_weekly_unsupported_weekday_errors(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.evaluate_schedule(
                {"type": "weekly", "weekday": "funday", "due_time": "09:00"},
                State(),
                datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
            )


class TestMonthlySchedule(unittest.TestCase):
    """Monthly schedule calculations."""

    def test_monthly_due_window(self) -> None:
        now = datetime(2026, 7, 1, 19, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "monthly",
                "day": 1,
                "due_time": "18:00",
                "overdue_time": "22:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "due")
        self.assertEqual(result.due_at, datetime(2026, 7, 1, 18, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 1, 22, 0, tzinfo=UTC))
        self.assertTrue(result.due)
        self.assertFalse(result.overdue)

    def test_monthly_overdue_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 1, 22, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "monthly",
                "day": 1,
                "due_time": "18:00",
                "overdue_time": "22:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertFalse(result.due)
        self.assertTrue(result.overdue)

    def test_monthly_completed_advances_to_next_month(self) -> None:
        now = datetime(2026, 7, 1, 19, 0, tzinfo=UTC)
        due_at = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "monthly",
                "day": 1,
                "due_time": "18:00",
                "overdue_time": "22:00",
            },
            State(
                last_completed=datetime(2026, 7, 1, 18, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 8, 1, 18, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 8, 1, 22, 0, tzinfo=UTC))

    def test_monthly_day_clamps_to_end_of_short_month(self) -> None:
        now = datetime(2027, 2, 27, 12, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "monthly",
                "day": 31,
                "due_time": "18:00",
                "overdue_time": "22:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2027, 2, 28, 18, 0, tzinfo=UTC))


class TestIntervalDaysSchedule(unittest.TestCase):
    """Interval-days schedule calculations."""

    def test_interval_days_initial_due_window_uses_today(self) -> None:
        now = datetime(2026, 7, 20, 13, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "interval_days",
                "every": 30,
                "due_time": "12:00",
                "overdue_time": "20:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "due")
        self.assertEqual(result.due_at, datetime(2026, 7, 20, 12, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 20, 20, 0, tzinfo=UTC))

    def test_interval_days_after_completion_uses_completed_obligation_anchor(self) -> None:
        now = datetime(2026, 7, 21, 13, 0, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "interval_days",
                "every": 30,
                "due_time": "12:00",
                "overdue_time": "20:00",
            },
            State(
                last_completed=datetime(2026, 7, 20, 13, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 8, 19, 12, 0, tzinfo=UTC))
        self.assertEqual(result.time_remaining, timedelta(days=28, hours=23))

    def test_interval_days_next_obligation_becomes_overdue_until_done(self) -> None:
        now = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "interval_days",
                "every": 30,
                "due_time": "12:00",
                "overdue_time": "20:00",
            },
            State(
                last_completed=datetime(2026, 7, 20, 13, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.due_at, datetime(2026, 8, 19, 12, 0, tzinfo=UTC))

    def test_interval_days_rejects_non_positive_interval(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.evaluate_schedule(
                {"type": "interval_days", "every": 0, "due_time": "09:00"},
                State(),
                datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
            )


class TestOneOffSchedule(unittest.TestCase):
    """One-off schedule calculations."""

    def test_one_off_pending_before_due_at(self) -> None:
        now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "one_off",
                "due_at": "2026-07-20T09:00:00+00:00",
                "overdue_at": "2026-07-20T10:00:00+00:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 7, 20, 9, 0, tzinfo=UTC))
        self.assertEqual(result.overdue_at, datetime(2026, 7, 20, 10, 0, tzinfo=UTC))

    def test_one_off_due_between_due_at_and_overdue_at(self) -> None:
        now = datetime(2026, 7, 20, 9, 30, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "one_off",
                "due_at": "2026-07-20T09:00:00+00:00",
                "overdue_at": "2026-07-20T10:00:00+00:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "due")
        self.assertTrue(result.due)
        self.assertFalse(result.overdue)

    def test_one_off_overdue_at_overdue_at(self) -> None:
        now = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "one_off",
                "due_at": "2026-07-20T09:00:00+00:00",
                "overdue_at": "2026-07-20T10:00:00+00:00",
            },
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertTrue(result.overdue)

    def test_one_off_without_overdue_at_preserves_strict_deadline(self) -> None:
        now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "one_off", "due_at": "2026-07-20T09:00:00+00:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.overdue_at, datetime(2026, 7, 20, 9, 0, tzinfo=UTC))

    def test_one_off_completed_stays_done(self) -> None:
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
        now = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {
                "type": "one_off",
                "due_at": "2026-07-20T09:00:00+00:00",
                "overdue_at": "2026-07-20T10:00:00+00:00",
            },
            State(
                last_completed=datetime(2026, 7, 20, 9, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, due_at)
        self.assertFalse(result.overdue)

    def test_one_off_rejects_overdue_at_before_due_at(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.evaluate_schedule(
                {
                    "type": "one_off",
                    "due_at": "2026-07-20T09:00:00+00:00",
                    "overdue_at": "2026-07-20T08:00:00+00:00",
                },
                State(),
                datetime(2026, 7, 20, 7, 0, tzinfo=UTC),
            )


class TestScheduleNormalization(unittest.TestCase):
    """Schedule config normalization."""

    def test_daily_defaults_overdue_time_to_due_time(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {"type": "daily", "due_time": "09:00"}
        )

        self.assertEqual(normalized["overdue_time"], "09:00")

    def test_weekly_keeps_explicit_overdue_time(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {
                "type": "weekly",
                "weekday": "wednesday",
                "due_time": "20:00",
                "overdue_time": "23:00",
            }
        )

        self.assertEqual(normalized["overdue_time"], "23:00")

    def test_normalization_rejects_earlier_overdue_time(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.normalize_schedule_config(
                {"type": "daily", "due_time": "20:00", "overdue_time": "19:00"}
            )

    def test_monthly_defaults_overdue_time_to_due_time(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {"type": "monthly", "day": 1, "due_time": "18:00"}
        )

        self.assertEqual(normalized["overdue_time"], "18:00")

    def test_interval_days_defaults_overdue_time_to_due_time(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {"type": "interval_days", "every": 30, "due_time": "12:00"}
        )

        self.assertEqual(normalized["overdue_time"], "12:00")

    def test_one_off_due_at_parses_successfully(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {
                "type": "one_off",
                "due_at": "2027-01-17T18:00:00",
                "overdue_at": "2027-01-17T21:00:00",
            }
        )

        self.assertEqual(normalized["due_at"], "2027-01-17T18:00:00")
        self.assertEqual(normalized["overdue_at"], "2027-01-17T21:00:00")

    def test_one_off_defaults_overdue_at_to_due_at(self) -> None:
        normalized = schedule.normalize_schedule_config(
            {"type": "one_off", "due_at": "2027-01-17T18:00:00"}
        )

        self.assertEqual(normalized["overdue_at"], "2027-01-17T18:00:00")

    def test_unknown_schedule_type_rejected(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.normalize_schedule_config({"type": "yearly"})


if __name__ == "__main__":
    unittest.main()
