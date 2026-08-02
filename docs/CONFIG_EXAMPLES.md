# Tracked Tasks — Configuration and Automation Examples

## Example YAML configuration

The same configuration is available as a copy-paste file at [examples/configuration.yaml](../examples/configuration.yaml).

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

    dishwasher_salt:
      name: Dishwasher Salt
      schedule:
        type: monthly
        day: 1
        due_time: "18:00"
        overdue_time: "22:00"

    morning_medication:
      name: Morning Medication
      schedule:
        type: daily
        due_time: "09:30"
        overdue_time: "10:00"

    strict_task_example:
      name: Strict Task Example
      schedule:
        type: daily
        due_time: "09:00"
        # overdue_time omitted, so overdue_time defaults to due_time

    change_filter:
      name: Change Filter
      schedule:
        type: interval_days
        every: 30
        due_time: "12:00"
        overdue_time: "20:00"

    rsvp_deadline:
      name: RSVP Deadline
      schedule:
        type: one_off
        due_at: "2027-01-17T18:00:00"
        overdue_at: "2027-01-17T21:00:00"
```

## Due vs overdue semantics

For this task:

```yaml
bins:
  name: Bins
  schedule:
    type: weekly
    weekday: wednesday
    due_time: "20:00"
    overdue_time: "23:00"
```

Expected lifecycle for an incomplete occurrence:

```text
Before Wednesday 20:00   -> pending
Wednesday 20:00-23:00    -> due
After Wednesday 23:00    -> overdue
After pressing mark done -> done
Next occurrence          -> pending again
```

If a recurring occurrence is overdue and incomplete, it stays overdue until the next occurrence reaches its own due time. For example, a daily bedtime task that became overdue at 23:00 remains overdue after midnight, then the next day's occurrence takes over at the next `due_time`.

If `overdue_time` is omitted, it defaults to `due_time`, preserving strict-deadline behaviour.

For one-off tasks, `due_at` starts the active/reminder window and optional `overdue_at` starts the final overdue state. If `overdue_at` is omitted, it defaults to `due_at`.

Schedule times are local Home Assistant wall-clock times. For example, in the UK, `due_time: "20:00"` means 20:00 during both BST and GMT.

For now, `overdue_time` must be equal to or later than `due_time`; cross-midnight due windows are not supported yet.

## Expected entities

For `bins`, expect entities like:

```text
sensor.bins_status
sensor.bins_last_completed
sensor.bins_next_due
sensor.bins_time_remaining
binary_sensor.bins_due
binary_sensor.bins_overdue
button.bins_mark_done
```

## NFC tag automation

These automation examples are also collected in [examples/automations.yaml](../examples/automations.yaml).

Recommended completion path:

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

## Zigbee button automation

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

## Dashboard button

The integration exposes `button.<task>_mark_done`, so a normal entities card can be used. This example is also available in [examples/dashboard.yaml](../examples/dashboard.yaml).

```yaml
type: entities
entities:
  - entity: sensor.bins_status
  - entity: sensor.bins_time_remaining
  - entity: sensor.bins_next_due
  - entity: sensor.bins_last_completed
  - entity: binary_sensor.bins_due
  - entity: binary_sensor.bins_overdue
  - entity: button.bins_mark_done
```

## Persistence check

After pressing `button.bins_mark_done`, restart Home Assistant. The integration restores `sensor.bins_last_completed` and the completed obligation timestamp from Home Assistant-native storage, so `sensor.bins_status`, `binary_sensor.bins_due`, and `binary_sensor.bins_overdue` should remain correct for the same occurrence.

## Gentle due reminder automation

Use the due sensor for softer reminders once the active window starts.

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

## Overdue notification automation

Use the overdue sensor for stronger reminders once the acceptable deadline has passed.

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

## Escalating overdue reminder example

This is intentionally outside the integration. The integration exposes state; normal Home Assistant automations decide what to do with that state.

```yaml
alias: Escalate bins reminder
trigger:
  - platform: state
    entity_id: binary_sensor.bins_overdue
    to: "on"
    for: "00:30:00"
condition:
  - condition: state
    entity_id: binary_sensor.bins_overdue
    state: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      flash: short
  - service: notify.mobile_app_your_phone
    data:
      message: "Bins are still overdue."
```

## Optional compatibility service

`tracked_tasks.mark_done` is secondary compatibility behaviour. The recommended public automation path is still `button.press`.

```yaml
service: tracked_tasks.mark_done
target:
  entity_id: button.bins_mark_done
```
