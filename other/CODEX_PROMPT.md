# Initial Codex Prompt — Build `tracked_tasks` Home Assistant Integration

I want you to build a custom Home Assistant integration called `tracked_tasks`.

Please read `AGENTS.md` and the files in `docs/` before making changes. Follow the staged implementation plan rather than trying to build every future feature at once.

## Goal

Build a native-feeling Home Assistant custom integration for household task tracking.

Each task should be defined once in YAML and should appear in Home Assistant as a device with related entities. Inputs like NFC tags, Zigbee buttons, dashboard buttons, or future Todoist sync should all mark the same task complete through a single integration service/action.

The core service/action should be:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

## Start with these stages

Please implement Stages 1–3 first, then stop and summarise what was built, how to install it, and how to test it.

Stages 1–3 are:

1. Custom integration skeleton that loads from YAML.
2. Basic task device/entities:
   - `sensor.<task>_status`
   - `sensor.<task>_last_completed`
3. Completion path:
   - `tracked_tasks.mark_done` service/action
   - `button.<task>_mark_done`
   - button and service update the same task state

## Initial YAML target

Support this config shape initially:

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

For Stages 1–3, the schedule can be parsed and stored but does not need full due/overdue calculation yet.

## Expected file structure

Create at least:

```text
custom_components/tracked_tasks/
  __init__.py
  manifest.json
  const.py
  sensor.py
  button.py
  services.yaml
  strings.json
```

You may also create supporting files such as:

```text
models.py
schedule.py
storage.py
binary_sensor.py
```

if useful, but keep the first implementation simple.

## Behaviour for first implementation

- Home Assistant should load the integration from YAML.
- Each configured task should create a Home Assistant device.
- Each task should expose a status sensor and last-completed sensor.
- Each task should expose a mark-done button.
- Calling `tracked_tasks.mark_done` should update the task’s last completed timestamp.
- Pressing the mark-done button should update the same state.
- Entities should refresh without needing to restart Home Assistant.
- Use stable `unique_id` values.
- Use `device_info` so the task’s entities are grouped under one device.

## State model for Stages 1–3

A simple in-memory state is acceptable initially:

```python
last_completed: datetime | None
```

Status may be:

- `pending` if never completed
- `done` if completed at least once

Persistence, due/overdue logic, and recurrence can come in later stages.

## After implementing Stages 1–3

Please provide:

1. A summary of changed/created files.
2. Install instructions.
3. Example `configuration.yaml`.
4. Example NFC automation using `tracked_tasks.mark_done`.
5. Known limitations.
6. Recommended next step, likely Stage 4 schedule calculation and Stage 5 due/overdue entities.

## Coding expectations

- Use modern Python and type hints.
- Keep Home Assistant integration glue clear and readable.
- Avoid blocking I/O.
- Keep the first version understandable for someone who has not built a HA custom integration before.
- Do not add Todoist, config flow, HACS, or persistence until the basic integration works.
