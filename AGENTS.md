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

## Current architectural decision

Each configured task should appear as a Home Assistant device.

Example for a `bins` task:

```text
Device: Bins
  sensor.bins_status
  sensor.bins_last_completed
  sensor.bins_next_due
  sensor.bins_time_remaining
  binary_sensor.bins_due
  binary_sensor.bins_overdue
  button.bins_mark_done
```

The preferred completion path is:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

It is acceptable to keep a `tracked_tasks.mark_done` service as a backwards-compatible convenience, but the task button entity is the canonical user-facing “method” for completing the task.

Do not build a pseudo-OOP service namespace such as `bins.mark_done` or `tracked_tasks.bins_mark_done`. That is not idiomatic Home Assistant. The idiomatic Home Assistant object model is:

```text
Task object       -> Home Assistant device
Task properties   -> sensors / binary sensors
Task methods      -> button entities or entity-targeted services
Task events       -> state changes / automation triggers
```

## Stage 5A architectural update: due window vs overdue deadline

Stages 4 and 5 may already calculate a status lifecycle where a task goes directly from `pending` to `overdue` at `due_time`. That is too blunt for household tasks.

The integration should now distinguish between:

```text
The time a task becomes active / worth reminding about
```

and:

```text
The time a task has truly breached its acceptable deadline
```

Use this model:

```text
pending -> due -> overdue -> done
```

Semantics:

- `pending` — the current/upcoming occurrence exists, but it is not yet in its active due window.
- `due` — the task should now be done and gentle reminders can begin, but it has not yet missed its final acceptable deadline.
- `overdue` — the task has breached its final acceptable deadline and is still incomplete.
- `done` — the current occurrence has been completed.

Add optional `overdue_time` support to schedule config.

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

For this example:

```text
Before Wednesday 20:00   -> pending
Wednesday 20:00-23:00    -> due
After Wednesday 23:00    -> overdue
After pressing mark done -> done
Next occurrence          -> pending again
```

If `overdue_time` is omitted, it should default to `due_time` to preserve existing behaviour.

For strict tasks, these two are equivalent:

```yaml
schedule:
  type: daily
  due_time: "09:00"
```

```yaml
schedule:
  type: daily
  due_time: "09:00"
  overdue_time: "09:00"
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
- Full historical reporting
- Multiple due windows per day, unless already implemented and only needs adapting

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

### Stage 5A — Separate due time and overdue time

Goal: Add an optional overdue deadline so `due` is a meaningful active/reminder window, not an unused or instantaneous state.

Config addition:

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

Rules:

- `due_time` is when the task enters the `due` state.
- `overdue_time` is when the task enters the `overdue` state.
- If `overdue_time` is omitted, default it to `due_time`.
- Existing configs with only `due_time` must continue to work.
- `binary_sensor.<task>_due` should turn on during the due window only when the current occurrence is incomplete.
- `binary_sensor.<task>_overdue` should turn on only after the overdue deadline when the current occurrence is incomplete.
- `sensor.<task>_status` should report `due` between `due_time` and `overdue_time`, and `overdue` after `overdue_time`.
- Marking the task done before, during, or after the due/overdue window should complete the current occurrence and move status to `done`.

Acceptance criteria:

- Existing Stage 4/5 behaviour remains unchanged when `overdue_time` is not configured.
- A task with `due_time: "20:00"` and `overdue_time: "23:00"` is `due`, not `overdue`, at 21:00.
- The same task becomes `overdue` at/after 23:00 if incomplete.
- The due and overdue binary sensors reflect that distinction.
- Unit tests or schedule-level tests cover before due, during due, after overdue, done before due, done during due, and done after overdue.

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
- example due reminder automation
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

For example, bins due Wednesday between 20:00 and 23:00 should be modelled as:

```text
Task: Bins
Current obligation active from: Wednesday 20:00
Current obligation overdue after: Wednesday 23:00
Completed at: not yet
Status: pending/due/overdue/done
```

Completion should apply to the current obligation, not blindly reset an interval from the current time unless the schedule type explicitly works that way.

## Important edge cases

When implementing schedule logic, think through and test:

- Home Assistant restarts
- Task completed before the due time on the same obligation
- Task completed during the due window
- Task completed after it became overdue
- Completion before the due date and whether it should count for the upcoming obligation
- Twice-daily or multiple-per-day schedules later, though not needed in v1
- Monthly schedules on days that do not exist in every month
- Daylight saving time changes
- `unknown` / missing / corrupt persisted state
- `overdue_time` earlier than `due_time`
- One-off tasks where `due_at` is used instead of `due_time`

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
