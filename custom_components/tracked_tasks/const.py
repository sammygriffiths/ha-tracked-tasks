"""Constants for the Tracked Tasks integration."""

from __future__ import annotations

DOMAIN = "tracked_tasks"
CONF_TASKS = "tasks"
CONF_SCHEDULE = "schedule"

PLATFORMS = ["sensor", "button"]

SERVICE_MARK_DONE = "mark_done"
ATTR_TASK_ID = "task_id"
ATTR_ENTITY_ID = "entity_id"

BUTTON_ENTITY_PREFIX = "button."
MARK_DONE_ENTITY_SUFFIX = "_mark_done"

STATUS_PENDING = "pending"
STATUS_DONE = "done"
