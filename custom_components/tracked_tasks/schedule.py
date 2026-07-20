"""Pure schedule calculation for tracked tasks.

Stage 4 intentionally supports only daily and weekly schedules. The output
models a task as a scheduled obligation identified by its due timestamp.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol


STATUS_PENDING = "pending"
STATUS_DUE = "due"
STATUS_OVERDUE = "overdue"
STATUS_DONE = "done"

SCHEDULE_DAILY = "daily"
SCHEDULE_WEEKLY = "weekly"

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class ScheduleError(ValueError):
    """Raised when a schedule cannot be calculated."""


class TaskStateLike(Protocol):
    """Minimal task state shape used by pure schedule calculation."""

    last_completed: datetime | None
    completed_due_at: datetime | None


@dataclass(frozen=True)
class ScheduleEvaluation:
    """Calculated state for a scheduled task obligation."""

    status: str
    due_at: datetime
    current_obligation_due_at: datetime
    current_obligation_completed: bool
    due: bool
    overdue: bool
    time_remaining: timedelta


def evaluate_schedule(
    schedule: Mapping[str, Any],
    state: TaskStateLike,
    now: datetime,
) -> ScheduleEvaluation:
    """Evaluate a daily or weekly task schedule at a point in time."""
    current_due_at = get_current_obligation_due_at(schedule, now)
    completed = state.completed_due_at == current_due_at

    if completed:
        due_at = get_next_obligation_due_at(schedule, current_due_at)
        return ScheduleEvaluation(
            status=STATUS_DONE,
            due_at=due_at,
            current_obligation_due_at=current_due_at,
            current_obligation_completed=True,
            due=False,
            overdue=False,
            time_remaining=max(due_at - now, timedelta()),
        )

    if now < current_due_at:
        return ScheduleEvaluation(
            status=STATUS_PENDING,
            due_at=current_due_at,
            current_obligation_due_at=current_due_at,
            current_obligation_completed=False,
            due=False,
            overdue=False,
            time_remaining=current_due_at - now,
        )

    return ScheduleEvaluation(
        status=STATUS_OVERDUE,
        due_at=current_due_at,
        current_obligation_due_at=current_due_at,
        current_obligation_completed=False,
        due=False,
        overdue=True,
        time_remaining=timedelta(),
    )


def get_current_obligation_due_at(
    schedule: Mapping[str, Any],
    now: datetime,
) -> datetime:
    """Return the due timestamp for the current scheduled obligation."""
    schedule_type = schedule.get("type")

    if schedule_type == SCHEDULE_DAILY:
        due_time = _parse_due_time(schedule)
        today_due = _combine(now.date(), due_time, now)
        if now < today_due:
            return today_due
        return today_due

    if schedule_type == SCHEDULE_WEEKLY:
        due_time = _parse_due_time(schedule)
        weekday = _parse_weekday(schedule)
        days_since_due = (now.weekday() - weekday) % 7
        days_until_due = (weekday - now.weekday()) % 7
        previous_due = _combine(now.date() - timedelta(days=days_since_due), due_time, now)
        upcoming_due = _combine(
            now.date() + timedelta(days=days_until_due),
            due_time,
            now,
        )

        if days_until_due < days_since_due:
            return upcoming_due
        if days_until_due == days_since_due and now < upcoming_due:
            return upcoming_due
        return previous_due

    raise ScheduleError(f"Unsupported schedule type: {schedule_type!r}")


def get_next_obligation_due_at(
    schedule: Mapping[str, Any],
    due_at: datetime,
) -> datetime:
    """Return the due timestamp after the supplied obligation due timestamp."""
    schedule_type = schedule.get("type")

    if schedule_type == SCHEDULE_DAILY:
        return due_at + timedelta(days=1)

    if schedule_type == SCHEDULE_WEEKLY:
        return due_at + timedelta(weeks=1)

    raise ScheduleError(f"Unsupported schedule type: {schedule_type!r}")


def _parse_due_time(schedule: Mapping[str, Any]) -> time:
    raw_due_time = schedule.get("due_time")
    if not isinstance(raw_due_time, str):
        raise ScheduleError("Schedule requires due_time as HH:MM")

    try:
        return time.fromisoformat(raw_due_time)
    except ValueError as err:
        raise ScheduleError(f"Invalid due_time: {raw_due_time!r}") from err


def _parse_weekday(schedule: Mapping[str, Any]) -> int:
    raw_weekday = schedule.get("weekday")
    if not isinstance(raw_weekday, str):
        raise ScheduleError("Weekly schedule requires weekday")

    weekday = WEEKDAYS.get(raw_weekday.lower())
    if weekday is None:
        raise ScheduleError(f"Invalid weekday: {raw_weekday!r}")

    return weekday


def _combine(day: date, due_time: time, now: datetime) -> datetime:
    return datetime.combine(day, due_time, tzinfo=now.tzinfo)
