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

- `tracked_tasks.mark_done` service/action
- `button.<task>_mark_done`
- `services.yaml`
- service/action translations in `strings.json` if appropriate

Acceptance criteria:

- Developer Tools → Actions can call `tracked_tasks.mark_done`.
- Calling the action updates `last_completed`.
- Pressing the task button updates the same state.
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
- example NFC automation
- example Zigbee button automation
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
