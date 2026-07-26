# Tracked Tasks — Architecture

## Overview

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices/entities.

The central concept is a scheduled task/obligation. Each task owns its own state and derived status. Inputs such as NFC tags, Zigbee buttons, dashboard buttons, Todoist completions, or voice commands should not implement task-specific timing logic. They should press the task's `button.<task>_mark_done` entity, or call an entity-targeted integration action that delegates to the same code path.

## Core design

```text
Input trigger
  NFC tag / Zigbee button / dashboard button / Todoist / voice
        ↓
button.press -> button.<task>_mark_done
        ↓
Tracked task state updates
        ↓
Entities update
  status / due / overdue / next_due / time_remaining / last_completed
        ↓
Normal Home Assistant automations react to entity state
```

## Why this exists

This avoids scattering each task across:

- helper entities
- template sensors
- timestamp update automations
- overdue logic automations
- notification automations

Instead, each task is defined once and exposed as a group of related entities under one Home Assistant device.

## Integration domain

```text
tracked_tasks
```

## Expected file structure

```text
custom_components/tracked_tasks/
  __init__.py
  manifest.json
  const.py
  models.py
  schedule.py
  storage.py
  sensor.py
  binary_sensor.py
  button.py
  services.yaml
  strings.json
```

Not all files are required in the first implementation, but schedule/status logic should be split out early so it can be tested independently.

## Data model

### Task config

A task config describes what the task is and when it is due/overdue.

Example:

```yaml
tracked_tasks:
  tasks:
    bins:
      name: Bins
      schedule:
        type: weekly
        weekday: wednesday
        due_time: "20:00"
        overdue_time: "23:00"
```

Suggested Python model:

```python
@dataclass(frozen=True)
class TaskConfig:
    task_id: str
    name: str
    schedule: ScheduleConfig
```

Suggested schedule model:

```python
@dataclass(frozen=True)
class ScheduleConfig:
    type: str
    due_time: time | None = None
    overdue_time: time | None = None
    weekday: str | None = None
    day: int | None = None
    every: int | None = None
    due_at: datetime | None = None
```

If `overdue_time` is omitted, it should be normalised to `due_time` for schedule types that use `due_time`.

### Task state

Task state describes what has happened.

Suggested model:

```python
@dataclass
class TaskState:
    last_completed: datetime | None = None
    completed_due_at: datetime | None = None
```

Depending on the recurrence model, storing `completed_due_at` may be more reliable than storing only `last_completed`.

## Status model

Statuses:

```text
pending  — not yet in the active due window
due      — current obligation is due/active but not overdue
overdue  — overdue deadline has passed and current obligation is incomplete
done     — current obligation has been completed
disabled — optional future state
```

## Due and overdue windows

The integration distinguishes between the start of the due/reminder window and the final overdue deadline.

```yaml
schedule:
  type: weekly
  weekday: wednesday
  due_time: "20:00"
  overdue_time: "23:00"
```

This means:

```text
Before Wednesday 20:00   -> pending
Wednesday 20:00-23:00    -> due
After Wednesday 23:00    -> overdue
After pressing mark done -> done for the current occurrence
```

If `overdue_time` is omitted, the integration should default it to `due_time`, preserving previous strict-deadline behaviour:

```yaml
schedule:
  type: daily
  due_time: "09:00"
```

is equivalent to:

```yaml
schedule:
  type: daily
  due_time: "09:00"
  overdue_time: "09:00"
```

For Stage 5A, `overdue_time` must be equal to or later than `due_time` on the same scheduled date. Cross-midnight windows such as `due_time: "23:00"` and `overdue_time: "01:00"` are intentionally rejected until the recurrence model explicitly supports them.

### Entity meaning

```text
binary_sensor.<task>_due
```

Should be `on` when the current occurrence is incomplete and now is between the occurrence's `due_time` and `overdue_time`.

```text
binary_sensor.<task>_overdue
```

Should be `on` when the current occurrence is incomplete and now is at or after the occurrence's `overdue_time`.

```text
sensor.<task>_status
```

Should return `pending`, `due`, `overdue`, or `done` based on the current occurrence.

## Supported schedules for v1/v2

### Daily

```yaml
schedule:
  type: daily
  due_time: "09:00"
  overdue_time: "09:30"
```

### Weekly

```yaml
schedule:
  type: weekly
  weekday: thursday
  due_time: "20:00"
  overdue_time: "23:00"
```

### Monthly

```yaml
schedule:
  type: monthly
  day: 1
  due_time: "18:00"
  overdue_time: "22:00"
```

### Interval days

```yaml
schedule:
  type: interval_days
  every: 30
  due_time: "18:00"
  overdue_time: "22:00"
```

### One-off

```yaml
schedule:
  type: one_off
  due_at: "2027-01-17T18:00:00"
  overdue_at: "2027-01-17T21:00:00"
```

For one-off schedules, `due_at` starts the active/reminder window and optional `overdue_at` starts the final overdue state. If `overdue_at` is omitted, it defaults to `due_at`, preserving strict-deadline behaviour.

Monthly schedules clamp days that do not exist in a shorter month to that month's final day. Interval-days schedules use the last completed obligation as their anchor once completed; before first completion, the initial occurrence is based on today's `due_time`.

## Entity design

Each task should become a Home Assistant device.

Suggested entities per task:

```text
sensor.<task>_status
sensor.<task>_last_completed
sensor.<task>_next_due
sensor.<task>_time_remaining
binary_sensor.<task>_due
binary_sensor.<task>_overdue
button.<task>_mark_done
```

All entities should share device info using identifiers like:

```python
("tracked_tasks", task_id)
```

## Services/actions

### Preferred mark-done path

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

This is the main user-facing API used by NFC tags, Zigbee buttons, dashboard controls, and future sync integrations.

### Optional compatibility service

If retained, this should delegate to the same shared completion method as the button entity:

```yaml
service: tracked_tasks.mark_done
target:
  entity_id: button.bins_mark_done
```

A legacy `data.task_id` form is acceptable only for backwards compatibility and should not be the primary documented path.

## Persistence

The integration should not rely on Home Assistant helper entities as its internal state store.

Task completion state is persisted using Home Assistant's native storage API. The current storage key is `tracked_tasks`, with storage version `1`.

Persist at least:

- `last_completed`
- `completed_due_at` or equivalent obligation identifier, if implemented

Current payload shape:

```json
{
  "version": 1,
  "tasks": {
    "bins": {
      "last_completed": "2026-07-23T20:10:00+00:00",
      "completed_due_at": "2026-07-23T20:00:00+00:00"
    }
  }
}
```

Missing, empty, old, unknown, or malformed task entries should be ignored during restore so bad stored data does not prevent Home Assistant startup.

## Future ideas

- Config flow UI
- Options flow UI
- Task enable/disable switch
- Skip current occurrence service/action
- Completion history sensor/attribute
- Todoist sync as optional input/mirror
- HACS packaging
- More complex recurrence rules
