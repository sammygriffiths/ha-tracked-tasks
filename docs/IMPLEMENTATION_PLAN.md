# Tracked Tasks — Implementation Plan

## Principle

Build in small, working stages. Do not start by building config flow, Todoist sync, full recurrence, persistence, and all entity types at once.

Each stage should be testable in Home Assistant before continuing.

## Current state assumption

Stages 1-3 have already been implemented once. The next task is a small architectural correction before continuing to due/overdue/persistence work.

The correction is: make the task's button entity the primary completion mechanism, instead of requiring users to call `tracked_tasks.mark_done` with a raw `task_id`.

## Stage 3A — Refactor completion API around task button entities

Goal: Preserve existing Stage 1-3 behaviour, but make the Home Assistant-native button entity the canonical completion path.

Preferred completion automation:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

Tasks:

1. Identify the existing shared mark-done/update-state code path.
2. Ensure `button.<task>_mark_done` calls that shared code path.
3. Update examples/docs so NFC and Zigbee automations use `button.press` targeting the button entity.
4. Review the existing `tracked_tasks.mark_done` service:
   - If kept, make it secondary.
   - Prefer adding support for `target.entity_id` if feasible.
   - If `task_id` remains, keep it for backwards compatibility and document it as legacy/compatibility-only.
5. Do not remove existing `task_id` support if doing so would break the already-tested Stage 1-3 implementation. Compatibility is better than churn at this stage.
6. Ensure all completion paths update the same state and refresh the same entities.

Acceptance criteria:

- `button.press` on `button.bins_mark_done` updates `sensor.bins_last_completed`.
- `button.press` on `button.bins_mark_done` updates `sensor.bins_status`.
- NFC automation examples use `button.press`, not `tracked_tasks.mark_done` with `task_id`.
- Zigbee automation examples use `button.press`, not `tracked_tasks.mark_done` with `task_id`.
- If `tracked_tasks.mark_done` still exists, it is documented as optional/compatibility behaviour.
- Integration still loads from YAML.
- Existing Stage 1-3 tests, if any, still pass.

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
- example NFC automation using `button.press`
- example Zigbee button automation using `button.press`
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
