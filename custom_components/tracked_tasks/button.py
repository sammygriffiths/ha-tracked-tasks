"""Button platform for Tracked Tasks."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .entity import TrackedTaskEntity
from .models import TrackedTask, TrackedTaskManager


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up tracked task buttons from YAML config."""
    manager: TrackedTaskManager = hass.data[DOMAIN]
    async_add_entities(
        TrackedTaskMarkDoneButton(task, manager)
        for task in manager.tasks.values()
    )


class TrackedTaskMarkDoneButton(TrackedTaskEntity, ButtonEntity):
    """Button that marks a tracked task done."""

    _attr_name = "Mark done"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, task: TrackedTask, manager: TrackedTaskManager) -> None:
        super().__init__(task, "mark_done")
        self._manager = manager

    async def async_press(self) -> None:
        """Mark the task done."""
        self._manager.async_mark_done(self.task.config.task_id)
