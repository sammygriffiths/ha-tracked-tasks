# Tracked Tasks

`tracked_tasks` is a custom Home Assistant integration for modelling household tasks as native Home Assistant devices and entities.

The first implementation supports YAML-defined tasks, basic status and last-completed sensors, and one shared completion path through `tracked_tasks.mark_done` or a task button.

## Installation

Copy this folder into your Home Assistant configuration directory:

```text
custom_components/tracked_tasks/
```

Then restart Home Assistant after adding your YAML configuration.

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

Each task appears as a Home Assistant device, with its entities grouped under that device.

## Service/action

All completion inputs should call the same service/action:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

The service and `button.bins_mark_done` update the same in-memory task state. The status sensor changes from `pending` to `done`, and the last-completed sensor updates to the current UTC timestamp.

## NFC automation example

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

## Known limitations

- Completion state is in memory only and is lost on Home Assistant restart.
- Schedule configuration is stored but not yet used for status calculation.
- Due, overdue, next due, and time remaining entities are not implemented yet.
- No config flow, options flow, Todoist sync, HACS metadata, or custom dashboard card is included.

## Roadmap

Recommended next stages:

1. Add Home Assistant-native persistence for `last_completed`.
2. Move schedule calculation into pure Python code with tests.
3. Add due/overdue, next due, and time remaining entities.
