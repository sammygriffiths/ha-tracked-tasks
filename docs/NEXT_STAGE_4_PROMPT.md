# Future Codex Prompt — Stage 4 Schedule Calculation

Use this only after Stage 3A has been implemented and tested.

I have tested Stage 3A of the `tracked_tasks` Home Assistant integration. The canonical completion path is now:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

Please now implement **Stage 4 schedule calculation only**.

## Goal

Move task schedule/status logic into pure Python code that can be unit-tested outside Home Assistant.

Add or update:

- `models.py`
- `schedule.py`
- tests, if a test structure exists

## Support initially

Implement daily and weekly schedules first:

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

Do not implement monthly, interval-days, one-off, persistence, config flow, Todoist, or HACS in this pass.

## Required calculation outputs

Given `now`, task config, and task state, the schedule module should be able to calculate:

- status
- current or next due timestamp
- due boolean
- overdue boolean
- time remaining
- whether the current obligation has already been completed

## Important model

A task should be treated as a scheduled obligation, not merely as `now - last_completed`.

Completion should apply to the current/upcoming obligation represented by a due timestamp or equivalent obligation identifier.

## Acceptance criteria

- Existing Stage 3A behaviour still works.
- Schedule logic can be tested without running Home Assistant.
- At least daily and weekly schedules are supported.
- Edge cases and unsupported cases are documented.
- Stop after Stage 4 and summarise the next recommended Stage 5 work.
