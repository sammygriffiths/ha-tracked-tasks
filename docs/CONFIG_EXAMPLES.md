# Tracked Tasks — Configuration and Automation Examples

## Example YAML configuration

```yaml
tracked_tasks:
  tasks:
    bins:
      name: Bins
      schedule:
        type: weekly
        weekday: thursday
        due_time: "09:00"

    dishwasher_salt:
      name: Dishwasher Salt
      schedule:
        type: monthly
        day: 1
        due_time: "18:00"

    morning_medication:
      name: Morning Medication
      schedule:
        type: daily
        due_time: "09:30"

    change_filter:
      name: Change Filter
      schedule:
        type: interval_days
        every: 30
        due_time: "12:00"

    rsvp_deadline:
      name: RSVP Deadline
      schedule:
        type: one_off
        due_at: "2027-01-17T18:00:00"
```

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

## Zigbee button automation

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

## Dashboard button

The integration should expose `button.<task>_mark_done`, so a normal entities card can be used:

```yaml
type: entities
entities:
  - entity: sensor.bins_status
  - entity: sensor.bins_time_remaining
  - entity: sensor.bins_next_due
  - entity: sensor.bins_last_completed
  - entity: binary_sensor.bins_overdue
  - entity: button.bins_mark_done
```

## Notification automation

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

## Escalating reminder example

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
