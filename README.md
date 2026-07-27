# Tracked Tasks

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices and entities.

The current implementation supports YAML-defined tasks, schedule-derived entities, persistent completion state, and one shared completion path through each task's mark-done button entity.

## Installation

Copy this folder into your Home Assistant configuration directory:

```text
custom_components/tracked_tasks/
```

Then add your YAML configuration and restart Home Assistant.

This version reports `0.1.9` in `manifest.json`.

## Quick start

1. Copy `custom_components/tracked_tasks/` into `/config/custom_components/tracked_tasks/`.
2. Add a `tracked_tasks:` block to `/config/configuration.yaml`.
3. Restart Home Assistant.
4. Open Settings -> Devices & services -> Devices and look for one device per configured task.
5. Press `button.<task>_mark_done` or call `button.press` against it from an automation.

## Configuration

Minimal weekly task:

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

Daily, weekly, monthly, interval-days, and one-off schedules are evaluated by pure Python schedule logic and exposed through Home Assistant entities.

Times such as `due_time: "20:00"` and `overdue_time: "23:00"` are interpreted in Home Assistant's configured local timezone. In the UK, that means `20:00` remains 20:00 local time during BST and GMT.

More complete examples are available in:

- [examples/configuration.yaml](examples/configuration.yaml)
- [docs/CONFIG_EXAMPLES.md](docs/CONFIG_EXAMPLES.md)

## Entities

For a task with ID `bins`, Home Assistant creates:

```text
sensor.bins_status
sensor.bins_last_completed
sensor.bins_next_due
sensor.bins_time_remaining
binary_sensor.bins_due
binary_sensor.bins_overdue
button.bins_mark_done
```

Each task appears as a Home Assistant device, with its entities grouped under that device. The YAML configuration is imported into a Home Assistant config entry so the device registry can attach the task entities to a real device.

If Home Assistant has already seen earlier versions of the entities, it may keep old entity IDs such as `sensor.last_completed` in the entity registry. Delete the old tracked task entities from Settings -> Devices & services -> Entities, and if a `Tracked Tasks` integration entry exists, delete that too. Then restart Home Assistant so the YAML import runs again and recreates entities with IDs such as `sensor.bins_last_completed`.

## Completion

The recommended completion path is Home Assistant's native `button.press` service targeting the task button entity:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

Pressing `button.bins_mark_done` in the UI uses the same path. The status sensor changes from `pending` to `done`, and the last-completed sensor updates to the current UTC timestamp.

`tracked_tasks.mark_done` is still available as a compatibility action for older automations. Prefer targeting the entity:

```yaml
service: tracked_tasks.mark_done
target:
  entity_id: button.bins_mark_done
```

Legacy `data.task_id` calls are also retained:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

When a supported schedule exists, completion also records which scheduled obligation was completed internally. For example, if `bins` is due Wednesday at 20:00 and you press the button on Wednesday evening, that completion is associated with that Wednesday 20:00 obligation.

## Persistence

Completion state is saved with Home Assistant's native storage API under the `tracked_tasks` storage key.

The stored payload is versioned and currently contains:

- `last_completed`
- `completed_due_at`

This lets the integration restore the last completion timestamp and the completed scheduled obligation after Home Assistant restarts. Missing, empty, old, or malformed stored data is ignored so startup can continue with a fresh in-memory state for affected tasks.

## Schedule calculation

The schedule module at `custom_components/tracked_tasks/schedule.py` has no Home Assistant imports and can be tested directly.

Supported schedule types:

```yaml
schedule:
  type: daily
  due_time: "09:00"
  overdue_time: "09:30"
```

```yaml
schedule:
  type: weekly
  weekday: wednesday
  due_time: "20:00"
  overdue_time: "23:00"
```

```yaml
schedule:
  type: monthly
  day: 1
  due_time: "18:00"
  overdue_time: "22:00"
```

```yaml
schedule:
  type: interval_days
  every: 30
  due_time: "12:00"
  overdue_time: "20:00"
```

```yaml
schedule:
  type: one_off
  due_at: "2027-01-17T18:00:00"
  overdue_at: "2027-01-17T21:00:00"
```

`due_time` starts the active/reminder window. `overdue_time` starts the final overdue state. If `overdue_time` is omitted, it defaults to `due_time`, preserving strict-deadline behavior.

For one-off schedules, `due_at` starts the active/reminder window and optional `overdue_at` starts the final overdue state. If `overdue_at` is omitted, it defaults to `due_at`, preserving strict-deadline behavior.

For one-off schedules without an explicit timezone offset, `due_at` and `overdue_at` are interpreted in Home Assistant's local timezone.

Strict behavior:

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

Given a schedule, task state, and `now`, the calculation returns:

- `status`
- `due_at`
- `overdue_at`
- `current_obligation_due_at`
- `current_obligation_completed`
- `due`
- `overdue`
- `time_remaining`

Current schedule semantics:

- Before the due timestamp, an incomplete task is `pending`.
- From the due timestamp until the overdue timestamp, an incomplete task is `due`.
- At or after the overdue timestamp, an incomplete task is `overdue`.
- If `completed_due_at` matches the current obligation due timestamp, the task is `done` and `due_at` advances to the next occurrence.
- `overdue_time` must be equal to or later than `due_time`; cross-midnight due windows are not supported yet.
- `time_remaining` counts down to `due_at` and is zero once due or overdue.
- Monthly schedules clamp days that do not exist in a shorter month to that month's final day.
- Interval-days schedules use the last completed obligation as their anchor once completed; before first completion, the initial occurrence is based on today's `due_time`.
- One-off schedules support an optional `overdue_at` and do not advance to another occurrence.

Home Assistant entity behavior:

- `sensor.<task>_status` uses schedule-derived status for supported schedule types.
- `sensor.<task>_next_due` exposes the current or next due timestamp.
- `sensor.<task>_time_remaining` exposes whole minutes remaining until due.
- `binary_sensor.<task>_due` turns on during the due window while incomplete.
- `binary_sensor.<task>_overdue` turns on when the current obligation is overdue.
- Schedule-derived entities refresh every minute and whenever the task is marked done.

## NFC automation example

```yaml
alias: Mark bins done from NFC
trigger:
  - platform: tag
    tag_id: YOUR_TAG_ID
action:
  - service: button.press
    target:
      entity_id: button.bins_mark_done
```

## Zigbee button automation example

```yaml
alias: Mark bins done from Zigbee button
trigger:
  - platform: state
    entity_id: sensor.bins_button_action
    to: "single"
action:
  - service: button.press
    target:
      entity_id: button.bins_mark_done
```

## Due reminder automation example

```yaml
alias: Gentle bins reminder
trigger:
  - platform: state
    entity_id: binary_sensor.bins_due
    to: "on"
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "Bins are due this evening."
```

## Overdue notification automation example

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

More automation examples are available in [examples/automations.yaml](examples/automations.yaml).

## Dashboard example

Use a normal Home Assistant entities card:

```yaml
type: entities
title: Bins
entities:
  - entity: sensor.bins_status
  - entity: sensor.bins_time_remaining
  - entity: sensor.bins_next_due
  - entity: sensor.bins_last_completed
  - entity: binary_sensor.bins_due
  - entity: binary_sensor.bins_overdue
  - entity: button.bins_mark_done
```

The same example is available in [examples/dashboard.yaml](examples/dashboard.yaml).

## Manual testing

1. Install the integration folder and add a `bins` task to `configuration.yaml`.
2. Restart Home Assistant and confirm these entities exist on one `Bins` device: `button.bins_mark_done`, `sensor.bins_status`, `sensor.bins_last_completed`, `sensor.bins_next_due`, `sensor.bins_time_remaining`, `binary_sensor.bins_due`, and `binary_sensor.bins_overdue`.
3. Press `button.bins_mark_done` in the UI and confirm `sensor.bins_last_completed` updates.
4. In Developer Tools -> Actions, call `button.press` targeting `button.bins_mark_done` and confirm the timestamp updates again.
5. Configure `due_time` a few minutes in the future and `overdue_time` a few minutes after that.
6. Confirm `sensor.bins_status` is `pending` before due, `due` during the due window, and `overdue` at/after the overdue deadline if incomplete.
7. Confirm `binary_sensor.bins_due` is on only during the due window, and `binary_sensor.bins_overdue` is on only after the overdue deadline.
8. Press `button.bins_mark_done` before, during, or after the window and confirm the task becomes `done`.
9. Optionally call the compatibility action with `target.entity_id` or legacy `data.task_id` and confirm it updates the same sensors.
10. Restart Home Assistant and confirm `sensor.bins_last_completed`, `sensor.bins_status`, `binary_sensor.bins_due`, and `binary_sensor.bins_overdue` still reflect the completed occurrence correctly.

## Troubleshooting

- If tasks do not appear, check Home Assistant logs for `tracked_tasks` config validation errors.
- If entities have old names such as `sensor.last_completed`, remove the stale tracked task entities from Settings -> Devices & services -> Entities, remove any stale imported `Tracked Tasks` integration entry, then restart Home Assistant.
- If a task never reaches `due`, check that `due_time`, `overdue_time`, and Home Assistant's timezone match your expectation.
- If a completion was persisted before version `0.1.9`, press the task's mark-done button once after upgrading if its restored status looks wrong. Earlier versions calculated obligations in UTC.
- If Home Assistant reports invalid YAML, start with the minimal weekly example above and add other tasks one at a time.

## Known limitations

- Full recurrence rules and daylight-saving edge cases are not implemented yet.
- Cross-midnight windows such as `due_time: "23:00"` with `overdue_time: "01:00"` are rejected for now.
- Interval-days schedules do not yet support an explicit start date.
- No UI config flow, options flow, Todoist sync, HACS metadata, or custom dashboard card is included.

## Roadmap

Recommended next stages:

1. Stage 8: optional future polish such as config flow, options flow, enable/disable controls, Todoist sync, HACS packaging, or brand images.
2. Add explicit start dates for interval-days schedules if needed.
3. Add cross-midnight due windows if needed.
