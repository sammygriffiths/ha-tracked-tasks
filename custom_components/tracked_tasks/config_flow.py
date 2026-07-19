"""Config flow for Tracked Tasks.

The first user-facing configuration path is still YAML. Home Assistant imports
that YAML into a config entry so entity device_info is honored by the device
registry.
"""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN


class TrackedTasksConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle YAML import for Tracked Tasks."""

    VERSION = 1

    async def async_step_import(
        self,
        import_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Import configuration from configuration.yaml."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured(updates=import_config)

        return self.async_create_entry(
            title="Tracked Tasks",
            data=import_config,
        )

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """YAML is the only supported setup path for now."""
        return self.async_abort(reason="yaml_only")
