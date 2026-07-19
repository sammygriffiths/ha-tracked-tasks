# Codex Prompt — Stage 3A Refactor Completion API

I have already had you implement Stages 1-3 of the `tracked_tasks` Home Assistant custom integration using the existing handoff docs.

Please read `AGENTS.md` and the files in `docs/` again, because the architecture has been refined.

## Background

The current implementation likely supports a service/action like this:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

That works, but I want the integration to feel more Home Assistant-native and more object-like.

Each configured task should be treated as a Home Assistant device. Its properties should be sensors/binary sensors, and its actions should be button entities or entity-targeted services.

So the preferred completion path should now be:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

In other words, `button.bins_mark_done` should be the canonical "mark this task done" action.

## Task for this pass

Please implement **Stage 3A only**: refactor or adjust the completion API so the task button entity is the primary user-facing completion path.

Do **not** continue into due/overdue scheduling, persistence, Todoist, config flow, or HACS in this pass.

## Requirements

1. Preserve the existing Stage 1-3 functionality.
2. Ensure each task still appears as a Home Assistant device.
3. Ensure each task still exposes:
   - `sensor.<task>_status`
   - `sensor.<task>_last_completed`
   - `button.<task>_mark_done`
4. Ensure pressing `button.<task>_mark_done` updates the same underlying task state used by the sensors.
5. Ensure automations can mark a task complete with:

   ```yaml
   service: button.press
   target:
     entity_id: button.bins_mark_done
   ```

6. Review the existing `tracked_tasks.mark_done` service/action:
   - Prefer keeping it for backwards compatibility if it already works.
   - If feasible, add support for entity targeting, e.g.

     ```yaml
     service: tracked_tasks.mark_done
     target:
       entity_id: button.bins_mark_done
     ```

   - If `data.task_id` remains supported, document it as compatibility/legacy usage rather than the primary recommended path.
7. Make sure all completion paths call one shared internal method/function so state handling does not diverge.
8. Update documentation and examples to use `button.press` as the recommended NFC/Zigbee/dashboard completion mechanism.
9. Add or update tests if the project currently has tests. At minimum, document manual test steps.

## Example automations that should appear in the docs

### NFC

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

### Zigbee button

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

## Acceptance criteria

Please stop after this stage and summarise what changed.

I should be able to verify:

1. Home Assistant loads the integration without errors.
2. `button.bins_mark_done` exists.
3. Pressing the button in the UI updates `sensor.bins_last_completed`.
4. Calling `button.press` against `button.bins_mark_done` updates `sensor.bins_last_completed`.
5. `sensor.bins_status` updates consistently.
6. Any retained `tracked_tasks.mark_done` service still works if it existed before, but docs now present it as optional/compatibility behaviour.
7. Documentation points to Stage 4 as the next step after this pass.

## After completing this pass

Please provide:

1. A concise summary of code changes.
2. Any breaking changes, if unavoidable.
3. Manual test instructions.
4. Updated example automations.
5. The recommended next Codex prompt/stage, which should be Stage 4 schedule calculation.
