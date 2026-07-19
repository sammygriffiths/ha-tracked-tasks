# AGENTS.md — Tracked Tasks Home Assistant Integration

## Project goal

Build a custom Home Assistant integration called `tracked_tasks`.

The integration models household obligations as first-class Home Assistant **devices with related entities**. The user wants to define a task once, then have Home Assistant expose related entities such as status, due state, overdue state, next due time, last completed time, time remaining, and a dashboard button to mark the task done.

The core design principle is:

> A task is the object. In Home Assistant terms, each task should be a logical device. The task's properties are entities, and the task's actions are button entities or entity-targeted services.

Do not build task logic directly into NFC automations. NFC tags, Zigbee buttons, dashboard buttons, Todoist, and other triggers are only inputs. They should all mark the same task complete by pressing/targeting the task's `button.<task>_mark_done` entity, or by using an entity-targeted integration action that delegates to the same code path.

## User context

The user is technically competent and has an OOP/programming background. They want this to feel like a clean object/entity model rather than a scattered set of helpers, templates, and automations.

They use Home Assistant, Zigbee2MQTT, NFC tags, dashboard cards, and may later want Todoist integration. They are comfortable editing YAML and source files, but this is their first custom Home Assistant integration.

## Target integration name

- Domain: `tracked_tasks`
- Friendly name: `Tracked Tasks`
- Main folder: `custom_components/tracked_tasks/`

## Important architectural correction after Stages 1-3

Stages 1-3 may already have implemented a procedural service like this:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

That should no longer be the primary user-facing API.

The preferred, Home Assistant-native model is:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

That `button.<task>_mark_done` entity is the canonical “method” for completing the task. It should update the same shared task state used by all other entities for that task.

It is acceptable to keep a `tracked_tasks.mark_done` service as a backwards-compatible convenience, but it should either:

1. Support `target.entity_id` and operate on one or more `button.<task>_mark_done` entities, or
2. Be clearly marked as legacy/deprecated if it still accepts `task_id`.

Do not build a pseudo-OOP service namespace such as `bins.mark_done` or `tracked_tasks.bins_mark_done`. That is not idiomatic Home Assistant. The idiomatic Home Assistant object model is:

```text
Task object       -> Home Assistant device
Task properties   -> sensors / binary sensors
Task methods      -> button entities or entity-targeted services
Task events       -> state changes / automation triggers
```

## Non-goals for the current change request

Do not build everything at once.

Avoid these unless explicitly requested later:

- Todoist sync
- External APIs
- AWS Lambda/DynamoDB/Pushbullet
- Config flow UI
- Options flow UI
- HACS packaging
- Complex frontend cards
- Full iCalendar/RRULE support
- Mobile app-specific notification logic
- Full persistence, unless it already exists and only needs preserving
- Full recurrence/due/overdue logic, unless explicitly part of the current stage

## Preferred staged delivery

Build this in stages. Each stage should leave the integration in a working/testable state.

### Stage 1 — Minimal integration skeleton

Create a custom integration that can be copied into `/config/custom_components/tracked_tasks/`.

It should include at least:

```text
custom_components/tracked_tasks/
  __init__.py
  manifest.json
  const.py
  sensor.py
  binary_sensor.py
  button.py
  services.yaml
  strings.json
```

Use YAML configuration initially, for example:

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

The integration should create one Home Assistant device per task.

### Stage 2 — Basic task entities

For each task, expose:

- `sensor.<task>_status`
- `sensor.<task>_last_completed`
- `button.<task>_mark_done`

Each task should appear as one device in Home Assistant, and these entities should be grouped under that device.

### Stage 3 — Primary completion path through button entities

Goal: All completion inputs can update task state through the same button/entity mechanism.

Canonical completion path:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

The button must update the shared underlying task state. Any convenience service/action must delegate to the same shared code path.

Acceptance criteria:

- Pressing `button.<task>_mark_done` updates `last_completed`.
- NFC automations can call `button.press` with the task button entity.
- Zigbee automations can call `button.press` with the task button entity.
- Sensors update without restarting Home Assistant.
- If `tracked_tasks.mark_done` remains, it is secondary and either supports `target.entity_id` or is documented as legacy.

### Stage 4 — Schedule calculation

Goal: Move schedule/status logic into pure Python code.

Add:

- `models.py`
- `schedule.py`

Support first:

- daily
- weekly

Then add:

- monthly
- interval days
- one-off

Acceptance criteria:

- Schedule logic is unit-testable outside Home Assistant.
- Given `now`, task config, and task state, code can calculate:
  - status
  - next due
  - overdue boolean
  - due boolean
  - time remaining

### Stage 5 — Due/overdue/next due entities

Goal: Expose derived task state to Home Assistant.

Add:

- `binary_sensor.<task>_due`
- `binary_sensor.<task>_overdue`
- `sensor.<task>_next_due`
- `sensor.<task>_time_remaining`

Acceptance criteria:

- Automations can trigger when `binary_sensor.<task>_overdue` turns on.
- Dashboard can show countdown/next due/last completed.
- States refresh as time passes, not only when mark_done is called.

### Stage 6 — Persistence

Goal: Completion state survives Home Assistant restarts.

Tasks:

- Persist task state using Home Assistant-native storage.
- Restore state on setup.
- Handle missing/corrupt stored state gracefully.

Acceptance criteria:

- Mark task done.
- Restart Home Assistant.
- `last_completed` remains correct.
- Status remains correct after restart.

### Stage 7 — Documentation and example automations

Goal: The user can install, configure, and use the integration.

Add/update:

- `README.md`
- example YAML config
- example NFC automation using `button.press`
- example Zigbee button automation using `button.press`
- example overdue notification automation
- known limitations

### Stage 8 — Optional future polish

Only after the above works:

- Config flow UI
- Options flow UI
- enable/disable task switch
- skip occurrence service/action
- Todoist sync
- HACS compatibility
- brand images

## Task model

A task should be treated as a scheduled obligation, not merely as a last-completed timestamp.

For example, bins due Thursday at 09:00 should be modelled as:

```text
Task: Bins
Current obligation due at: Thursday 09:00
Completed at: not yet
Status: due/overdue/etc.
```

Completion should apply to the current obligation, not blindly reset an interval from the current time unless the schedule type explicitly works that way.

## Important edge cases

When implementing schedule logic, think through and test:

- Home Assistant restarts
- Task completed before the due time on the same obligation
- Task completed after it became overdue
- Twice-daily or multiple-per-day schedules later, though not needed in v1
- Monthly schedules on days that do not exist in every month
- Daylight saving time changes
- `unknown` / missing / corrupt persisted state
- Whether completion before the due date should count for the upcoming obligation

For v1, document any edge case that is not yet supported.

## Entity/device requirements

Each task should appear as a Home Assistant device, with related entities grouped under it.

Entity examples for `bins`:

```text
sensor.bins_status
sensor.bins_last_completed
sensor.bins_next_due
sensor.bins_time_remaining
binary_sensor.bins_due
binary_sensor.bins_overdue
button.bins_mark_done
```

Each entity should have a stable `unique_id`.

Each entity should expose `device_info` with identifiers based on `(DOMAIN, task_id)` so Home Assistant groups the entities into one device.

## Service/action requirements

The preferred completion action is:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

Optional convenience service/action:

```yaml
service: tracked_tasks.mark_done
target:
  entity_id: button.bins_mark_done
```

Avoid making `task_id` the primary public API. If `task_id` is retained for backwards compatibility, document it as legacy or compatibility-only.

Optional later services/actions:

```yaml
tracked_tasks.skip_occurrence
tracked_tasks.reset_task
tracked_tasks.set_enabled
```

Prefer entity-targeted services/actions for these too, rather than raw `task_id` data fields.
