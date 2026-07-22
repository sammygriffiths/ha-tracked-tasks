# Tracked Tasks — Implementation Plan

## Principle

Build in small, working stages. Do not start by building config flow, Todoist sync, full recurrence, persistence, and all entity types at once.

Each stage should be testable in Home Assistant before continuing.

## Stage 1 — Skeleton

Goal: Home Assistant loads the custom integration without errors.

Tasks:

1. Create `custom_components/tracked_tasks/`.
2. Add `manifest.json`.
3. Add `const.py`.
4. Add `__init__.py` with YAML config parsing.
5. Validate a minimal `tracked_tasks:` YAML block.
6. Log loaded tasks at startup.

Acceptance criteria:

- Home Assistant starts without integration errors.
- Invalid config produces a useful error.
- Loaded tasks are visible in logs.

## Stage 2 — Status and last completed sensors

Goal: Each configured task creates a device and basic entities.

Entities:

- `sensor.<task>_status`
- `sensor.<task>_last_completed`

Acceptance criteria:

- Each task appears as a device in Home Assistant.
- Related entities are grouped under that device.
- Entities have stable unique IDs.
- Initial status is `pending` or `unknown`, depending on the chosen model.

## Stage 3 — mark_done service/action and button

Goal: All completion inputs can update task state through one mechanism.

Add:

- `button.<task>_mark_done`
- optional `tracked_tasks.mark_done` service/action
- `services.yaml`
- service/action translations in `strings.json` if appropriate

Acceptance criteria:

- Pressing `button.<task>_mark_done` updates the shared task state.
- Calling `button.press` against the task button updates `last_completed`.
- If retained, `tracked_tasks.mark_done` delegates to the same shared completion method.
- Sensors update without restarting Home Assistant.

## Stage 4 — Schedule calculation

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

## Stage 5 — Due/overdue/next due entities

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

## Stage 5A — Separate due and overdue times

Goal: Make `due` a useful reminder/active-window state by distinguishing it from the final overdue deadline.

### Problem being fixed

The current implementation may behave like this:

```text
pending -> overdue -> done
```

with `due_time` acting as an immediate overdue deadline. That leaves the `due` status unused or semantically unclear.

Household tasks often need a softer model:

```text
"Start reminding me at 20:00, but it is not truly overdue until 23:00."
```

### Config addition

Add optional `overdue_time` for schedule types that currently use `due_time`:

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

### Required semantics

- `due_time` is when the current occurrence becomes `due`.
- `overdue_time` is when the current occurrence becomes `overdue`.
- If `overdue_time` is omitted, default it to `due_time`.
- Existing configs with only `due_time` must keep working and behave as before.
- Reject `overdue_time` values that are earlier than `due_time`; cross-midnight due windows can be added later.
- Status should be:
  - `pending` before the occurrence's due time.
  - `due` from due time until overdue time, if incomplete.
  - `overdue` at/after overdue time, if incomplete.
  - `done` when the current occurrence has been completed.
- `binary_sensor.<task>_due` should be `on` only in the due window while incomplete.
- `binary_sensor.<task>_overdue` should be `on` only after the overdue deadline while incomplete.
- Pressing `button.<task>_mark_done` before, during, or after the due window should mark the current occurrence done.

### Acceptance criteria

- A weekly task with `due_time: "20:00"` and `overdue_time: "23:00"` is:
  - `pending` before 20:00.
  - `due` at/after 20:00 and before 23:00.
  - `overdue` at/after 23:00 if not complete.
  - `done` after pressing `button.<task>_mark_done`.
- The same task does not regress from `done` to `due` or `overdue` within the same occurrence.
- A strict task with no `overdue_time` behaves as before.
- Unit tests or pure schedule tests cover the new transition logic.
- Documentation and examples are updated.

## Stage 6 — Persistence

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

## Stage 7 — Documentation and example automations

Goal: The user can install, configure, and use the integration.

Add/update:

- `README.md`
- example YAML config
- example NFC automation using `button.press`
- example Zigbee button automation using `button.press`
- example due reminder automation
- example overdue notification automation
- known limitations

## Stage 8 — Optional future polish

Only after the above works:

- Config flow UI
- Options flow UI
- enable/disable task switch
- skip occurrence service/action
- Todoist sync
- HACS compatibility
- brand images
