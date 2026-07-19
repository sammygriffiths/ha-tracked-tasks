"""Sensor platform for Tracked Tasks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import TrackedTaskEntity
from .models import TrackedTask, TrackedTaskManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up tracked task sensors from a config entry."""
    manager: TrackedTaskManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for task in manager.tasks.values():
        entities.extend(
            [
                TrackedTaskStatusSensor(task, manager),
                TrackedTaskLastCompletedSensor(task, manager),
            ]
        )

    async_add_entities(entities)


class TrackedTaskSensorEntity(TrackedTaskEntity, SensorEntity):
    """Base class for tracked task sensors."""

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager, entity_key: str) -> None:
        super().__init__(task, Platform.SENSOR.value, entity_key)
        self._manager = manager
        self._remove_listener: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register for manager updates."""
        self._remove_listener = self._manager.async_add_listener(
            self._handle_manager_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from manager updates."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _handle_manager_update(self) -> None:
        """Write updated state to Home Assistant."""
        self.async_write_ha_state()


class TrackedTaskStatusSensor(TrackedTaskSensorEntity):
    """Expose the simple status for a tracked task."""

    _attr_name = "Status"
    _attr_icon = "mdi:checkbox-marked-circle-outline"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "status")

    @property
    def native_value(self) -> str:
        """Return the task status."""
        return self.task.state.status


class TrackedTaskLastCompletedSensor(TrackedTaskSensorEntity):
    """Expose the last completion timestamp for a tracked task."""

    _attr_name = "Last completed"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-check"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "last_completed")

    @property
    def native_value(self) -> datetime | None:
        """Return the last completion timestamp."""
        return self.task.state.last_completed
