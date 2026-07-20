"""Sensor platform for Tracked Tasks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
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
                TrackedTaskNextDueSensor(task, manager),
                TrackedTaskTimeRemainingSensor(task, manager),
            ]
        )

    async_add_entities(entities)


class TrackedTaskSensorEntity(TrackedTaskEntity, SensorEntity):
    """Base class for tracked task sensors."""

    def __init__(
        self,
        task: TrackedTask,
        manager: TrackedTaskManager,
        entity_key: str,
        entity_name: str,
    ) -> None:
        super().__init__(task, Platform.SENSOR.value, entity_key, entity_name)
        self._manager = manager
        self._remove_listener: Callable[[], None] | None = None
        self._remove_time_listener: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register for manager updates."""
        self._remove_listener = self._manager.async_add_listener(
            self._handle_manager_update
        )
        self._remove_time_listener = async_track_time_interval(
            self.hass,
            self._handle_time_update,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from manager updates."""
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


class TrackedTaskStatusSensor(TrackedTaskSensorEntity):
    """Expose the simple status for a tracked task."""

    _attr_icon = "mdi:checkbox-marked-circle-outline"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "status", "Status")

    @property
    def native_value(self) -> str:
        """Return the task status."""
        evaluation = self._manager.evaluate_task(self.task)
        if evaluation is not None:
            return evaluation.status

        return self.task.state.status


class TrackedTaskLastCompletedSensor(TrackedTaskSensorEntity):
    """Expose the last completion timestamp for a tracked task."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-check"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "last_completed", "Last completed")

    @property
    def native_value(self) -> datetime | None:
        """Return the last completion timestamp."""
        return self.task.state.last_completed


class TrackedTaskNextDueSensor(TrackedTaskSensorEntity):
    """Expose the next/current due timestamp for a tracked task."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "next_due", "Next due")

    @property
    def native_value(self) -> datetime | None:
        """Return the calculated due timestamp."""
        evaluation = self._manager.evaluate_task(self.task)
        if evaluation is None:
            return None

        return evaluation.due_at


class TrackedTaskTimeRemainingSensor(TrackedTaskSensorEntity):
    """Expose time remaining until the task due timestamp."""

    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, manager, "time_remaining", "Time remaining")

    @property
    def native_value(self) -> int | None:
        """Return whole minutes remaining until due."""
        evaluation = self._manager.evaluate_task(self.task)
        if evaluation is None:
            return None

        return max(0, int(evaluation.time_remaining.total_seconds() // 60))
