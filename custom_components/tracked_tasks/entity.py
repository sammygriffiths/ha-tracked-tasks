"""Shared entity helpers for Tracked Tasks."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import DOMAIN
from .models import TrackedTask


class TrackedTaskEntity(Entity):
    """Base entity for entities belonging to a tracked task device."""

    _attr_has_entity_name = True

    def __init__(self, task: TrackedTask, platform: str, entity_key: str) -> None:
        self.task = task
        self._attr_unique_id = f"{task.config.task_id}_{entity_key}"
        object_id = f"{slugify(task.config.task_id)}_{entity_key}"
        self._attr_suggested_object_id = object_id
        self.entity_id = f"{platform}.{object_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the tracked task."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.task.config.task_id)},
            name=self.task.config.name,
            manufacturer="Tracked Tasks",
            model="Tracked Task",
        )
