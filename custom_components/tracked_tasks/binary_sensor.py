"""Binary sensor platform for Tracked Tasks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .entity import TrackedTaskEntity
from .models import TrackedTask, TrackedTaskManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up tracked task binary sensors from a config entry."""
    manager: TrackedTaskManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for task in manager.tasks.values():
        entities.extend(
            [
                TrackedTaskDueBinarySensor(task, manager),
                TrackedTaskOverdueBinarySensor(task, manager),
            ]
        )

    async_add_entities(entities)


class TrackedTaskBinarySensorEntity(TrackedTaskEntity, BinarySensorEntity):
    """Base class for tracked task binary sensors."""

    def __init__(
        self,
        task: TrackedTask,
        manager: TrackedTaskManager,
        entity_key: str,
        entity_name: str,
    ) -> None:
        super().__init__(task, Platform.BINARY_SENSOR.value, entity_key, entity_name)
        self._manager = manager
        self._remove_listener: Callable[[], None] | None = None
        self._remove_time_listener: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register for manager and time updates."""
        self._remove_listener = self._manager.async_add_listener(
            self._handle_manager_update
        )
        self._remove_time_listener = async_track_time_interval(
            self.hass,
            self._handle_time_update,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from manager and time updates."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        if self._remove_time_listener is not None:
            self._remove_time_listener()
            self._remove_time_listener = None

    @callback
    def _handle_manager_update(self) -> None:
        """Write updated state to Home Assistant."""
        self.async_write_ha_state()

    @callback
    def _handle_time_update(self, now: datetime) -> None:
        """Write time-derived state to Home Assistant."""
        self.async_write_ha_state()


class TrackedTaskDueBinarySensor(TrackedTaskBinarySensorEntity):
    """Expose whether a tracked task is due."""

    _attr_icon = "mdi:calendar-alert"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "due", "Due")

    @property
    def is_on(self) -> bool:
        """Return true if the task is currently due."""
        evaluation = self._manager.evaluate_task(self.task)
        return evaluation.due if evaluation is not None else False


class TrackedTaskOverdueBinarySensor(TrackedTaskBinarySensorEntity):
    """Expose whether a tracked task is overdue."""

    _attr_icon = "mdi:calendar-remove"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "overdue", "Overdue")

    @property
    def is_on(self) -> bool:
        """Return true if the task is overdue."""
        evaluation = self._manager.evaluate_task(self.task)
        return evaluation.overdue if evaluation is not None else False
