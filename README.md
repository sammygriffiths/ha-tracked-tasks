# Tracked Tasks

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices and entities.

The first implementation supports YAML-defined tasks, basic status and last-completed sensors, and one shared completion path through each task's mark-done button entity.

## Installation

Copy this folder into your Home Assistant configuration directory:

```text
custom_components/tracked_tasks/
```

Then restart Home Assistant after adding your YAML configuration.

This version reports `0.1.2` in `manifest.json`.

## Configuration

Add tasks to `configuration.yaml`:

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

Daily and weekly schedules can now be evaluated by pure Python schedule logic, though the current Home Assistant entities still expose only the Stage 3A status and last-completed values until Stage 5 wires schedule outputs into entities.

## Entities

For a task with ID `bins`, Home Assistant creates:

```text
sensor.bins_status
sensor.bins_last_completed
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

When a supported schedule exists, completion also records which scheduled obligation was completed internally. For example, if `bins` is due Thursday at 09:00 and you press the button on Wednesday evening, that completion is associated with the upcoming Thursday 09:00 obligation.

## Schedule calculation

Stage 4 adds a pure Python schedule module at `custom_components/tracked_tasks/schedule.py`. It has no Home Assistant imports and can be tested directly.

Supported schedule types:

```yaml
schedule:
  type: daily
  due_time: "09:00"
```

```yaml
schedule:
  type: weekly
  weekday: thursday
  due_time: "09:00"
```

Given a schedule, task state, and `now`, the calculation returns:

- `status`
- `due_at`
- `current_obligation_due_at`
- `current_obligation_completed`
- `due`
- `overdue`
- `time_remaining`

Current Stage 4 semantics:

- Before the due timestamp, an incomplete task is `pending`.
- At or after the due timestamp, an incomplete task is `overdue`.
- If `completed_due_at` matches the current obligation due timestamp, the task is `done` and `due_at` advances to the next occurrence.
- `due` is currently always `false`; a separate due window can be added later.
- `time_remaining` counts down to `due_at` and is zero once overdue.

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

## Manual testing

1. Install the integration folder and add a `bins` task to `configuration.yaml`.
2. Restart Home Assistant and confirm `button.bins_mark_done`, `sensor.bins_status`, and `sensor.bins_last_completed` exist on one `Bins` device.
3. Press `button.bins_mark_done` in the UI and confirm `sensor.bins_last_completed` updates.
4. In Developer Tools -> Actions, call `button.press` targeting `button.bins_mark_done` and confirm the timestamp updates again.
5. Confirm `sensor.bins_status` is `pending` before first completion and `done` after completion.
6. Optionally call the compatibility action with `target.entity_id` or legacy `data.task_id` and confirm it updates the same sensors.

## Known limitations

- Completion state is in memory only and is lost on Home Assistant restart.
- Schedule calculation supports only `daily` and `weekly` schedules.
- Monthly, interval-days, one-off schedules, full recurrence rules, and daylight-saving edge cases are not implemented yet.
- Schedule outputs are pure Python only in Stage 4; due, overdue, next due, and time remaining entities are not implemented yet.
- No UI config flow, options flow, Todoist sync, HACS metadata, or custom dashboard card is included.

## Roadmap

Recommended next stages:

1. Stage 5: add due/overdue, next due, and time remaining entities using the schedule module.
2. Add refresh behavior so schedule-derived entities update as time passes.
3. Add Home Assistant-native persistence for `last_completed`.
