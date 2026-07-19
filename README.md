# Tracked Tasks

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices and entities.

The first implementation supports YAML-defined tasks, basic status and last-completed sensors, and one shared completion path through each task's mark-done button entity.

## Installation

Copy this folder into your Home Assistant configuration directory:

```text
custom_components/tracked_tasks/
```

Then restart Home Assistant after adding your YAML configuration.

This version reports `0.1.1` in `manifest.json`.

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

The schedule is parsed and stored in this stage, but it is not yet used for due or overdue calculation.

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
- Schedule configuration is stored but not yet used for status calculation.
- Due, overdue, next due, and time remaining entities are not implemented yet.
- No config flow, options flow, Todoist sync, HACS metadata, or custom dashboard card is included.

## Roadmap

Recommended next stages:

1. Stage 4: move schedule calculation into pure Python code with tests.
2. Add due/overdue, next due, and time remaining entities.
3. Add Home Assistant-native persistence for `last_completed`.
