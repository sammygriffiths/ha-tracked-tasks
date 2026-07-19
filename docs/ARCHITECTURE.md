# Tracked Tasks — Architecture

## Overview

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices/entities.

The central concept is a scheduled task/obligation. Each task owns its own state and derived status. Inputs such as NFC tags, Zigbee buttons, dashboard buttons, Todoist completions, or voice commands should not implement task-specific timing logic. They should call the same integration action/service to mark a task complete.

## Core design

```text
Input trigger
  NFC tag / Zigbee button / dashboard button / Todoist / voice
        ↓
tracked_tasks.mark_done(task_id)
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

Not all files are required in the very first implementation, but schedule/status logic should be split out early so it can be tested independently.

## Data model

### Task config

A task config describes what the task is and when it is due.

Example:

```yaml
tracked_tasks:
  tasks:
    bins:
      name: Bins
      schedule:
        type: weekly
        weekday: thursday
        due_time: "09:00"
```

Suggested Python model:

```python
@dataclass(frozen=True)
class TaskConfig:
    task_id: str
    name: str
    schedule: ScheduleConfig
```

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

Initial statuses:

```text
pending  — not yet in the active due/overdue window
due      — current obligation is due but not overdue
overdue  — deadline has passed and current obligation is incomplete
done     — current obligation has been completed
disabled — optional future state
```

## Due windows

For v1, keep the model simple:

- `next_due` is the deadline timestamp for the current/upcoming obligation.
- A task becomes `overdue` when `now >= next_due` and that obligation has not been completed.
- Whether a task has a separate `due` state before being overdue can be configured later. In v1, `due` may simply mean “the obligation is current but not yet overdue”, or it may be omitted if the model is not ready.

Document the chosen semantics clearly.

## Supported schedules for v1/v2

### Daily

```yaml
schedule:
  type: daily
  due_time: "09:00"
```

### Weekly

```yaml
schedule:
  type: weekly
  weekday: thursday
  due_time: "09:00"
```

### Monthly

```yaml
schedule:
  type: monthly
  day: 1
  due_time: "18:00"
```

### Interval days

```yaml
schedule:
  type: interval_days
  every: 30
  due_time: "18:00"
```

### One-off

```yaml
schedule:
  type: one_off
  due_at: "2027-01-17T18:00:00"
```

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

### mark_done

Marks the current task obligation as complete.

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

This is the main integration API used by NFC tags, buttons, dashboard controls, and future sync integrations.

## Persistence

The integration should not rely on Home Assistant helper entities as its internal state store.

Persist task completion state using Home Assistant-native storage. In early development, in-memory state is acceptable only for Stage 1/2 proof of concept.

Persist at least:

- `last_completed`
- `completed_due_at` or equivalent obligation identifier, if implemented

## Future ideas

- Config flow UI
- Options flow UI
- Task enable/disable switch
- Skip current occurrence service
- Completion history sensor/attribute
- Todoist sync as optional input/mirror
- HACS packaging
- More complex recurrence rules
