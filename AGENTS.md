# AGENTS.md — Tracked Tasks Home Assistant Integration

## Project goal

Build a custom Home Assistant integration called `tracked_tasks`.

The integration models household obligations as first-class Home Assistant devices/entities. The user wants to define a task once, then have Home Assistant expose related entities such as status, due state, overdue state, next due time, last completed time, time remaining, and a dashboard button to mark the task done.

The core design principle is:

> NFC tags, Zigbee buttons, dashboard buttons, Todoist, and other triggers are only inputs. They should all call the same integration service/action to mark a task complete.

Do not build task logic directly into NFC automations. The task object/integration should own task state and due/overdue calculations.

## User context

The user is technically competent and has an OOP/programming background. They want this to feel like a clean object/entity model rather than a scattered set of helpers, templates, and automations.

They use Home Assistant, Zigbee2MQTT, NFC tags, dashboard cards, and may later want Todoist integration. They are comfortable editing YAML and source files, but this is their first custom Home Assistant integration.

## Target integration name

- Domain: `tracked_tasks`
- Friendly name: `Tracked Tasks`
- Main folder: `custom_components/tracked_tasks/`

## Non-goals for the first version

Do not build everything at once.

Avoid these in the initial implementation unless explicitly requested later:

- Todoist sync
- External APIs
- AWS Lambda/DynamoDB/Pushbullet
- Config flow UI
- Options flow UI
- HACS packaging
- Complex frontend cards
- Full iCalendar/RRULE support
- Mobile app-specific notification logic

The first goal is a reliable native-feeling Home Assistant integration with task entities and a `mark_done` action/service.

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

### Stage 2 — Basic entities and mark-done action

For each task, expose:

- `sensor.<task>_status`
- `sensor.<task>_last_completed`
- `button.<task>_mark_done`

Register an action/service:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

The service/action and the button must update the same underlying task state.

### Stage 3 — Due and overdue state

Add:

- `binary_sensor.<task>_due`
- `binary_sensor.<task>_overdue`
- `sensor.<task>_next_due`
- `sensor.<task>_time_remaining`

The integration should calculate task status from the schedule and completion state.

Initial status values:

- `pending` — not currently due yet
- `due` — currently in the due window but not yet overdue
- `overdue` — deadline has passed without completion
- `done` — current obligation has been completed
- `disabled` — optional later state, not required in v1

### Stage 4 — Persistence

Persist task completion state across Home Assistant restarts.

At minimum, persist:

- `last_completed`
- current/last completed obligation identifier or due timestamp, if needed

Use Home Assistant-native storage patterns where appropriate. Avoid using helpers such as `input_datetime` as the integration’s internal source of truth.

### Stage 5 — Recurrence support

Support these schedule types first:

#### Daily

```yaml
schedule:
  type: daily
  due_time: "09:00"
```

#### Weekly

```yaml
schedule:
  type: weekly
  weekday: thursday
  due_time: "09:00"
```

#### Monthly by day of month

```yaml
schedule:
  type: monthly
  day: 1
  due_time: "18:00"
```

#### Interval days

```yaml
schedule:
  type: interval_days
  every: 30
  due_time: "18:00"
```

#### One-off

```yaml
schedule:
  type: one_off
  due_at: "2027-01-17T18:00:00"
```

Do not over-engineer recurrence in v1. Add clean tests around each supported schedule type.

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

Register at least this action/service:

```yaml
tracked_tasks.mark_done:
  task_id: string
```

Optional later services/actions:

```yaml
tracked_tasks.reset_task:
  task_id: string

tracked_tasks.skip_current:
  task_id: string

tracked_tasks.set_enabled:
  task_id: string
  enabled: boolean
```

Do not add optional services until the core model is stable.

## Dashboard expectations

The integration should support a simple Lovelace dashboard using native entity cards or Mushroom-style cards.

The user should be able to show:

- task status
- time remaining
- next due
- last completed
- overdue state
- mark done button

No custom frontend card is required.

## Automation examples that should work

### NFC tag marks task done

```yaml
alias: Mark bins done from NFC
trigger:
  - platform: tag
    tag_id: YOUR_TAG_ID
action:
  - service: tracked_tasks.mark_done
    data:
      task_id: bins
```

### Zigbee button marks task done

```yaml
alias: Mark bins done from button
trigger:
  - platform: state
    entity_id: sensor.bins_button_action
    to: "single"
action:
  - service: tracked_tasks.mark_done
    data:
      task_id: bins
```

### Notify when overdue

```yaml
alias: Notify when bins overdue
trigger:
  - platform: state
    entity_id: binary_sensor.bins_overdue
    to: "on"
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "Bins have not been done yet."
```

## Testing expectations

Add tests where practical, especially for pure schedule/status logic.

At minimum, separate recurrence/status calculation into pure Python functions/classes so they can be unit tested without a running Home Assistant instance.

Prioritise tests for:

- daily due/overdue
- weekly due/overdue
- monthly due/overdue
- one-off due/overdue
- completion before due time
- completion after overdue time
- persisted state restoration

## Code style expectations

- Use modern Python with type hints.
- Prefer clear domain objects/dataclasses for task config/state.
- Keep Home Assistant platform glue thin.
- Keep schedule/status calculation in testable pure Python modules.
- Avoid blocking I/O in async Home Assistant code.
- Use Home Assistant-native APIs and patterns.
- Keep the initial implementation understandable for someone new to custom integrations.

## Documentation expectations

Update or create Markdown docs explaining:

- installation
- YAML configuration
- available entities
- available services/actions
- example automations
- known limitations
- staged roadmap

Do not leave the project without usable README-style guidance.
