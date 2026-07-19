"""The Tracked Tasks integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTITY_ID,
    ATTR_TASK_ID,
    BUTTON_ENTITY_PREFIX,
    CONF_SCHEDULE,
    CONF_TASKS,
    DOMAIN,
    MARK_DONE_ENTITY_SUFFIX,
    PLATFORMS,
    SERVICE_MARK_DONE,
)
from .models import TaskConfig, TrackedTaskManager

_LOGGER = logging.getLogger(__name__)

TASK_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required(CONF_SCHEDULE): vol.Schema(
            {
                vol.Required("type"): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TASKS): vol.Schema(
                    {cv.string: TASK_SCHEMA}
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

MARK_DONE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_TASK_ID): cv.string,
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Tracked Tasks from YAML."""
    hass.data.setdefault(DOMAIN, {})
    _async_register_services(hass)

    domain_config = config.get(DOMAIN)
    if domain_config is None:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=domain_config,
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tracked Tasks from a config entry."""
    task_configs = _parse_task_configs(entry.data[CONF_TASKS])
    manager = TrackedTaskManager(task_configs)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    _LOGGER.info(
        "Loaded %d tracked task(s): %s",
        len(task_configs),
        ", ".join(task_configs),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Tracked Tasks config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_MARK_DONE):
        return

    async def async_handle_mark_done(call: ServiceCall) -> None:
        manager_task_pairs = _tasks_from_mark_done_call(hass, call)
        for manager, task_id in manager_task_pairs:
            task = manager.async_mark_done(task_id)
            _LOGGER.info("Marked tracked task '%s' done", task.config.task_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_DONE,
        async_handle_mark_done,
        schema=MARK_DONE_SCHEMA,
    )


def _parse_task_configs(raw_tasks: dict[str, dict[str, Any]]) -> dict[str, TaskConfig]:
    """Convert YAML task dictionaries into task config objects."""
    return {
        task_id: TaskConfig(
            task_id=task_id,
            name=task_config["name"],
            schedule=task_config[CONF_SCHEDULE],
        )
        for task_id, task_config in raw_tasks.items()
    }


def _tasks_from_mark_done_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> list[tuple[TrackedTaskManager, str]]:
    """Resolve target task IDs from a compatibility mark_done service call."""
    task_ids: list[str] = []

    for entity_id in call.data.get(ATTR_ENTITY_ID, []):
        task_ids.append(_task_id_from_mark_done_entity_id(entity_id))

    if ATTR_TASK_ID in call.data:
        task_ids.append(call.data[ATTR_TASK_ID])

    if not task_ids:
        raise HomeAssistantError(
            "Provide either target.entity_id for a mark-done button or data.task_id"
        )

    manager_task_pairs: list[tuple[TrackedTaskManager, str]] = []
    unknown_task_ids: list[str] = []
    for task_id in list(dict.fromkeys(task_ids)):
        manager = _manager_for_task_id(hass, task_id)
        if manager is None:
            unknown_task_ids.append(task_id)
            continue
        manager_task_pairs.append((manager, task_id))

    if unknown_task_ids:
        raise HomeAssistantError(
            f"Unknown tracked task(s): {', '.join(unknown_task_ids)}"
        )

    return manager_task_pairs


def _manager_for_task_id(
    hass: HomeAssistant,
    task_id: str,
) -> TrackedTaskManager | None:
    """Find the manager that owns a task ID."""
    for manager in hass.data.get(DOMAIN, {}).values():
        if manager.get_task(task_id) is not None:
            return manager

    return None


def _task_id_from_mark_done_entity_id(entity_id: str) -> str:
    """Resolve a task ID from a mark-done button entity ID."""
    if not entity_id.startswith(BUTTON_ENTITY_PREFIX) or not entity_id.endswith(
        MARK_DONE_ENTITY_SUFFIX
    ):
        raise HomeAssistantError(
            "tracked_tasks.mark_done target.entity_id must be a "
            "button.<task>_mark_done entity"
        )

    return entity_id[
        len(BUTTON_ENTITY_PREFIX) : -len(MARK_DONE_ENTITY_SUFFIX)
    ]
