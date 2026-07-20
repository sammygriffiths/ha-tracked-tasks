"""Tests for pure tracked task schedule calculation."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


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
            {"type": "daily", "due_time": "09:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 7, 20, 9, 0, tzinfo=UTC))
        self.assertFalse(result.due)
        self.assertFalse(result.overdue)
        self.assertEqual(result.time_remaining, timedelta(minutes=30))
        self.assertFalse(result.current_obligation_completed)

    def test_daily_overdue_at_due_time(self) -> None:
        now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertTrue(result.overdue)
        self.assertEqual(result.time_remaining, timedelta())

    def test_daily_completed_before_due_time(self) -> None:
        now = datetime(2026, 7, 20, 8, 30, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00"},
            State(
                last_completed=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.current_obligation_due_at, due_at)
        self.assertEqual(result.due_at, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))
        self.assertTrue(result.current_obligation_completed)

    def test_daily_completed_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
        due_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "daily", "due_time": "09:00"},
            State(
                last_completed=datetime(2026, 7, 20, 9, 30, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))
        self.assertFalse(result.overdue)


class TestWeeklySchedule(unittest.TestCase):
    """Weekly schedule calculations."""

    def test_weekly_pending_before_due_day(self) -> None:
        now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)  # Monday

        result = schedule.evaluate_schedule(
            {"type": "weekly", "weekday": "thursday", "due_time": "09:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.due_at, datetime(2026, 7, 23, 9, 0, tzinfo=UTC))
        self.assertEqual(result.time_remaining, timedelta(days=3, hours=1))

    def test_weekly_overdue_after_due_day(self) -> None:
        now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)  # Friday

        result = schedule.evaluate_schedule(
            {"type": "weekly", "weekday": "thursday", "due_time": "09:00"},
            State(),
            now,
        )

        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.due_at, datetime(2026, 7, 23, 9, 0, tzinfo=UTC))
        self.assertTrue(result.overdue)

    def test_weekly_completed_before_due_time(self) -> None:
        now = datetime(2026, 7, 22, 19, 0, tzinfo=UTC)  # Wednesday
        due_at = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "weekly", "weekday": "thursday", "due_time": "09:00"},
            State(
                last_completed=datetime(2026, 7, 22, 18, 0, tzinfo=UTC),
                completed_due_at=due_at,
            ),
            now,
        )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.due_at, datetime(2026, 7, 30, 9, 0, tzinfo=UTC))

    def test_weekly_completed_after_overdue_time(self) -> None:
        now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)  # Friday
        due_at = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)

        result = schedule.evaluate_schedule(
            {"type": "weekly", "weekday": "thursday", "due_time": "09:00"},
            State(
                last_completed=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
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


class TestUnsupportedSchedules(unittest.TestCase):
    """Unsupported schedule types fail explicitly."""

    def test_monthly_not_implemented_yet(self) -> None:
        with self.assertRaises(schedule.ScheduleError):
            schedule.evaluate_schedule(
                {"type": "monthly", "day": 1, "due_time": "09:00"},
                State(),
                datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
            )


if __name__ == "__main__":
    unittest.main()
