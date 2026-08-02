"""Pure schedule calculation for tracked tasks.

The output models a task as a scheduled obligation identified by its due
timestamp, with an optional later overdue deadline.
"""

from __future__ import annotations

import calendar
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
SCHEDULE_MONTHLY = "monthly"
SCHEDULE_INTERVAL_DAYS = "interval_days"
SCHEDULE_ONE_OFF = "one_off"

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

SCHEDULES_WITH_DUE_TIME = {
    SCHEDULE_DAILY,
    SCHEDULE_WEEKLY,
    SCHEDULE_MONTHLY,
    SCHEDULE_INTERVAL_DAYS,
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
    overdue_at: datetime
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
    """Evaluate a task schedule at a point in time."""
    current_due_at = get_current_obligation_due_at(schedule, now, state)
    current_overdue_at = get_overdue_at(schedule, current_due_at)
    completed = state.completed_due_at == current_due_at

    if completed:
        due_at = get_next_obligation_due_at(schedule, current_due_at)
        return ScheduleEvaluation(
            status=STATUS_DONE,
            due_at=due_at,
            overdue_at=get_overdue_at(schedule, due_at),
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
            overdue_at=current_overdue_at,
            current_obligation_due_at=current_due_at,
            current_obligation_completed=False,
            due=False,
            overdue=False,
            time_remaining=current_due_at - now,
        )

    if now < current_overdue_at:
        return ScheduleEvaluation(
            status=STATUS_DUE,
            due_at=current_due_at,
            overdue_at=current_overdue_at,
            current_obligation_due_at=current_due_at,
            current_obligation_completed=False,
            due=True,
            overdue=False,
            time_remaining=timedelta(),
        )

    return ScheduleEvaluation(
        status=STATUS_OVERDUE,
        due_at=current_due_at,
        overdue_at=current_overdue_at,
        current_obligation_due_at=current_due_at,
        current_obligation_completed=False,
        due=False,
        overdue=True,
        time_remaining=timedelta(),
    )


def get_current_obligation_due_at(
    schedule: Mapping[str, Any],
    now: datetime,
    state: TaskStateLike | None = None,
) -> datetime:
    """Return the due timestamp for the current scheduled obligation."""
    schedule_type = schedule.get("type")

    if schedule_type == SCHEDULE_DAILY:
        due_time = _parse_due_time(schedule)
        today_due = _combine(now.date(), due_time, now)
        if now < today_due:
            return _select_between_previous_and_upcoming_due(
                today_due - timedelta(days=1),
                today_due,
                state,
            )
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
            return _select_between_previous_and_upcoming_due(
                previous_due,
                upcoming_due,
                state,
            )
        if days_until_due == days_since_due and now < upcoming_due:
            return _select_between_previous_and_upcoming_due(
                previous_due,
                upcoming_due,
                state,
            )
        return previous_due

    if schedule_type == SCHEDULE_MONTHLY:
        due_time = _parse_due_time(schedule)
        day = _parse_month_day(schedule)
        due_at = _combine(_monthly_due_date(now.year, now.month, day), due_time, now)
        if now < due_at:
            return _select_between_previous_and_upcoming_due(
                _previous_monthly_due_at(due_at, day),
                due_at,
                state,
            )
        return due_at

    if schedule_type == SCHEDULE_INTERVAL_DAYS:
        due_time = _parse_due_time(schedule)
        every = _parse_every_days(schedule)
        if state is not None and state.completed_due_at is not None:
            due_at = state.completed_due_at + timedelta(days=every)
            while now >= due_at + timedelta(days=every):
                due_at += timedelta(days=every)
            return due_at

        today_due = _combine(now.date(), due_time, now)
        if now < today_due:
            return today_due - timedelta(days=every)
        return today_due

    if schedule_type == SCHEDULE_ONE_OFF:
        return _parse_due_at(schedule, now)

    raise ScheduleError(f"Unsupported schedule type: {schedule_type!r}")


def normalize_schedule_config(schedule: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized schedule config with default overdue_time applied."""
    normalized = dict(schedule)
    schedule_type = normalized.get("type")
    if schedule_type not in SCHEDULES_WITH_DUE_TIME:
        if schedule_type == SCHEDULE_ONE_OFF:
            due_at = _parse_due_at(normalized, datetime.now().astimezone())
            overdue_at = _parse_overdue_at(normalized, due_at)
            if overdue_at < due_at:
                raise ScheduleError("overdue_at must be equal to or later than due_at")
            normalized.setdefault("overdue_at", normalized["due_at"])
            return normalized
        raise ScheduleError(f"Unsupported schedule type: {schedule_type!r}")

    due_time = _parse_due_time(normalized)
    overdue_time = _parse_overdue_time(normalized, due_time)
    normalized.setdefault("overdue_time", due_time.isoformat(timespec="minutes"))

    if schedule_type == SCHEDULE_WEEKLY:
        _parse_weekday(normalized)
    elif schedule_type == SCHEDULE_MONTHLY:
        _parse_month_day(normalized)
    elif schedule_type == SCHEDULE_INTERVAL_DAYS:
        _parse_every_days(normalized)

    return normalized


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

    if schedule_type == SCHEDULE_MONTHLY:
        day = _parse_month_day(schedule)
        year = due_at.year
        month = due_at.month + 1
        if month > 12:
            year += 1
            month = 1
        return _combine(_monthly_due_date(year, month, day), due_at.time(), due_at)

    if schedule_type == SCHEDULE_INTERVAL_DAYS:
        return due_at + timedelta(days=_parse_every_days(schedule))

    if schedule_type == SCHEDULE_ONE_OFF:
        return due_at

    raise ScheduleError(f"Unsupported schedule type: {schedule_type!r}")


def _select_between_previous_and_upcoming_due(
    previous_due_at: datetime,
    upcoming_due_at: datetime,
    state: TaskStateLike | None,
) -> datetime:
    """Return previous incomplete due or upcoming due before the upcoming window."""
    if state is not None and state.completed_due_at == previous_due_at:
        return upcoming_due_at
    if state is not None and state.completed_due_at == upcoming_due_at:
        return upcoming_due_at

    return previous_due_at


def get_overdue_at(
    schedule: Mapping[str, Any],
    due_at: datetime,
) -> datetime:
    """Return the overdue deadline for the supplied obligation due timestamp."""
    if schedule.get("type") == SCHEDULE_ONE_OFF:
        return _parse_overdue_at(schedule, due_at)

    due_time = _parse_due_time(schedule)
    overdue_time = _parse_overdue_time(schedule, due_time)
    return _combine(due_at.date(), overdue_time, due_at)


def _parse_due_time(schedule: Mapping[str, Any]) -> time:
    raw_due_time = schedule.get("due_time")
    if not isinstance(raw_due_time, str):
        raise ScheduleError("Schedule requires due_time as HH:MM")

    try:
        return time.fromisoformat(raw_due_time)
    except ValueError as err:
        raise ScheduleError(f"Invalid due_time: {raw_due_time!r}") from err


def _parse_overdue_time(schedule: Mapping[str, Any], due_time: time) -> time:
    raw_overdue_time = schedule.get("overdue_time", schedule.get("due_time"))
    if not isinstance(raw_overdue_time, str):
        raise ScheduleError("Schedule requires overdue_time as HH:MM")

    try:
        overdue_time = time.fromisoformat(raw_overdue_time)
    except ValueError as err:
        raise ScheduleError(f"Invalid overdue_time: {raw_overdue_time!r}") from err

    if overdue_time < due_time:
        raise ScheduleError("overdue_time must be equal to or later than due_time")

    return overdue_time


def _parse_weekday(schedule: Mapping[str, Any]) -> int:
    raw_weekday = schedule.get("weekday")
    if not isinstance(raw_weekday, str):
        raise ScheduleError("Weekly schedule requires weekday")

    weekday = WEEKDAYS.get(raw_weekday.lower())
    if weekday is None:
        raise ScheduleError(f"Invalid weekday: {raw_weekday!r}")

    return weekday


def _parse_month_day(schedule: Mapping[str, Any]) -> int:
    raw_day = schedule.get("day")
    if not isinstance(raw_day, int):
        raise ScheduleError("Monthly schedule requires day")
    if raw_day < 1 or raw_day > 31:
        raise ScheduleError("Monthly schedule day must be between 1 and 31")

    return raw_day


def _parse_every_days(schedule: Mapping[str, Any]) -> int:
    raw_every = schedule.get("every")
    if not isinstance(raw_every, int):
        raise ScheduleError("Interval-days schedule requires every")
    if raw_every < 1:
        raise ScheduleError("Interval-days schedule every must be at least 1")

    return raw_every


def _parse_due_at(schedule: Mapping[str, Any], now: datetime) -> datetime:
    raw_due_at = schedule.get("due_at")
    if not isinstance(raw_due_at, str):
        raise ScheduleError("One-off schedule requires due_at")

    try:
        due_at = datetime.fromisoformat(raw_due_at)
    except ValueError as err:
        raise ScheduleError(f"Invalid due_at: {raw_due_at!r}") from err

    if due_at.tzinfo is None:
        return due_at.replace(tzinfo=now.tzinfo)

    return due_at


def _parse_overdue_at(schedule: Mapping[str, Any], due_at: datetime) -> datetime:
    raw_overdue_at = schedule.get("overdue_at")
    if raw_overdue_at is None:
        return due_at
    if not isinstance(raw_overdue_at, str):
        raise ScheduleError("One-off overdue_at must be an ISO datetime")

    try:
        overdue_at = datetime.fromisoformat(raw_overdue_at)
    except ValueError as err:
        raise ScheduleError(f"Invalid overdue_at: {raw_overdue_at!r}") from err

    if overdue_at.tzinfo is None:
        overdue_at = overdue_at.replace(tzinfo=due_at.tzinfo)

    if overdue_at < due_at:
        raise ScheduleError("overdue_at must be equal to or later than due_at")

    return overdue_at


def _monthly_due_date(year: int, month: int, day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _previous_monthly_due_at(due_at: datetime, day: int) -> datetime:
    year = due_at.year
    month = due_at.month - 1
    if month < 1:
        year -= 1
        month = 12

    return _combine(_monthly_due_date(year, month, day), due_at.time(), due_at)


def _combine(day: date, due_time: time, now: datetime) -> datetime:
    return datetime.combine(day, due_time, tzinfo=now.tzinfo)
