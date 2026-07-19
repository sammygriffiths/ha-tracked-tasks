"""Button platform for Tracked Tasks."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import TrackedTaskEntity
from .models import TrackedTask, TrackedTaskManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up tracked task buttons from a config entry."""
    manager: TrackedTaskManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TrackedTaskMarkDoneButton(task, manager)
        for task in manager.tasks.values()
    )


class TrackedTaskMarkDoneButton(TrackedTaskEntity, ButtonEntity):
    """Button that marks a tracked task done."""

    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, Platform.BUTTON.value, "mark_done", "Mark done")
        self._manager = manager

    async def async_press(self) -> None:
        """Mark the task done."""
        self._manager.async_mark_done(self.task.config.task_id)
