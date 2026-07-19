"""The Tracked Tasks integration."""

from __future__ import annotations

import logging
from asyncio import gather
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_TASK_ID,
    CONF_SCHEDULE,
    CONF_TASKS,
    DOMAIN,
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

MARK_DONE_SCHEMA = vol.Schema({vol.Required(ATTR_TASK_ID): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Tracked Tasks from YAML."""
    domain_config = config.get(DOMAIN)
    if domain_config is None:
        return True

    task_configs = _parse_task_configs(domain_config[CONF_TASKS])
    manager = TrackedTaskManager(task_configs)
    hass.data[DOMAIN] = manager

    _LOGGER.info(
        "Loaded %d tracked task(s): %s",
        len(task_configs),
        ", ".join(task_configs),
    )

    async def async_handle_mark_done(call: ServiceCall) -> None:
        task_id = call.data[ATTR_TASK_ID]
        if manager.get_task(task_id) is None:
            raise HomeAssistantError(f"Unknown tracked task: {task_id}")

        task = manager.async_mark_done(task_id)
        _LOGGER.info("Marked tracked task '%s' done", task.config.task_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_DONE,
        async_handle_mark_done,
        schema=MARK_DONE_SCHEMA,
    )

    await gather(
        *(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
            for platform in PLATFORMS
        )
    )
    return True


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
