"""Small domain models for tracked household tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .const import STATUS_DONE, STATUS_PENDING
from .schedule import (
    ScheduleError,
    ScheduleEvaluation,
    evaluate_schedule,
    get_current_obligation_due_at,
)


@dataclass(frozen=True, slots=True)
class TaskConfig:
    """Configuration for one tracked task."""

    task_id: str
    name: str
    schedule: Mapping[str, Any]


@dataclass(slots=True)
class TaskState:
    """Runtime state for one tracked task.

    Persistence is intentionally deferred until the next implementation stage.
    """

    last_completed: datetime | None = None
    completed_due_at: datetime | None = None

    @property
    def status(self) -> str:
        """Return the simple stage 1-3 status."""
        return STATUS_DONE if self.last_completed is not None else STATUS_PENDING


@dataclass(slots=True)
class TrackedTask:
    """A configured task plus its current runtime state."""

    config: TaskConfig
    state: TaskState = field(default_factory=TaskState)


class TrackedTaskManager:
    """Own task state and notify entities when task state changes."""

    def __init__(self, tasks: Mapping[str, TaskConfig]) -> None:
        self.tasks: dict[str, TrackedTask] = {
            task_id: TrackedTask(config=task_config)
            for task_id, task_config in tasks.items()
        }
        self._listeners: set[Callable[[], None]] = set()

    def get_task(self, task_id: str) -> TrackedTask | None:
        """Return a tracked task by ID."""
        return self.tasks.get(task_id)

    def evaluate_task(
        self,
        task: TrackedTask,
        now: datetime | None = None,
    ) -> ScheduleEvaluation | None:
        """Evaluate a task schedule, if the schedule is supported."""
        try:
            return evaluate_schedule(
                task.config.schedule,
                task.state,
                now or datetime.now(timezone.utc),
            )
        except ScheduleError:
            return None

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to task state changes."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def async_mark_done(self, task_id: str) -> TrackedTask:
        """Mark a task done and notify subscribers."""
        task = self.tasks[task_id]
        completed_at = datetime.now(timezone.utc)
        task.state.last_completed = completed_at
        try:
            task.state.completed_due_at = get_current_obligation_due_at(
                task.config.schedule,
                completed_at,
            )
        except ScheduleError:
            task.state.completed_due_at = None
        self._notify_listeners()
        return task

    def _notify_listeners(self) -> None:
        """Notify subscribed entities that state has changed."""
        for listener in list(self._listeners):
            listener()
