"""Constants for the Tracked Tasks integration."""

from __future__ import annotations

DOMAIN = "tracked_tasks"
CONF_TASKS = "tasks"
CONF_SCHEDULE = "schedule"

PLATFORMS = ["sensor", "button"]

SERVICE_MARK_DONE = "mark_done"
ATTR_TASK_ID = "task_id"

STATUS_PENDING = "pending"
STATUS_DONE = "done"
