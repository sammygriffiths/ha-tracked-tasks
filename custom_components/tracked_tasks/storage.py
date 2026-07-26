"""Home Assistant storage helpers for tracked task state."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .models import TaskState, TrackedTask

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "tracked_tasks"
STORAGE_VERSION = 1
STORAGE_DATA_VERSION = 1
TASKS_KEY = "tasks"


class TrackedTasksStorage:
    """Persist tracked task runtime state with Home Assistant's storage API."""

    def __init__(self, hass: HomeAssistant) -> None:
        from homeassistant.helpers.storage import Store

        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(
        self,
        task_ids: Iterable[str],
    ) -> dict[str, TaskState]:
        """Load stored task states, ignoring data that cannot be restored."""
        from .models import TaskState

        data = await self._store.async_load()
        return deserialize_task_states(data, task_ids, TaskState)

    async def async_save(self, tasks: Mapping[str, TrackedTask]) -> None:
        """Save all configured task states."""
        await self._store.async_save(serialize_task_states(tasks))


def serialize_task_states(tasks: Mapping[str, TrackedTask]) -> dict[str, Any]:
    """Serialize task states into the integration storage payload."""
    return {
        "version": STORAGE_DATA_VERSION,
        TASKS_KEY: {
            task_id: {
                "last_completed": _format_datetime(task.state.last_completed),
                "completed_due_at": _format_datetime(task.state.completed_due_at),
            }
            for task_id, task in tasks.items()
        },
    }


def deserialize_task_states(
    data: Any,
    task_ids: Iterable[str],
    state_factory: Callable[..., TaskState],
) -> dict[str, TaskState]:
    """Deserialize stored states for currently configured tasks.

    Bad or unknown entries are intentionally skipped so malformed storage does not
    prevent Home Assistant from starting.
    """
    if data is None:
        return {}

    if not isinstance(data, dict):
        _LOGGER.warning("Ignoring tracked task storage because it is not an object")
        return {}

    raw_tasks = _raw_task_states(data)
    if raw_tasks is None:
        return {}

    states: dict[str, TaskState] = {}
    for task_id in task_ids:
        raw_state = raw_tasks.get(task_id)
        if raw_state is None:
            continue
        if not isinstance(raw_state, dict):
            _LOGGER.warning("Ignoring stored tracked task '%s': state is invalid", task_id)
            continue

        states[task_id] = state_factory(
            last_completed=_parse_datetime(raw_state.get("last_completed")),
            completed_due_at=_parse_datetime(raw_state.get("completed_due_at")),
        )

    return states


def _raw_task_states(data: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the task state mapping from current or simple legacy payloads."""
    raw_tasks = data.get(TASKS_KEY)
    if isinstance(raw_tasks, dict):
        return raw_tasks

    if raw_tasks is not None:
        _LOGGER.warning("Ignoring tracked task storage because 'tasks' is invalid")
        return None

    if all(isinstance(value, dict) for value in data.values()):
        return data

    return None


def _format_datetime(value: datetime | None) -> str | None:
    """Format a datetime for storage."""
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime from storage."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        _LOGGER.warning("Ignoring invalid tracked task datetime: %r", value)
        return None
