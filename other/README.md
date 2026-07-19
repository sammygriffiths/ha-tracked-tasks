# Tracked Tasks Codex Handoff

This folder contains handoff material for Codex to build a custom Home Assistant integration called `tracked_tasks`.

## Files

- `AGENTS.md` — main project instructions and constraints for Codex
- `CODEX_PROMPT.md` — current prompt to paste into Codex
- `docs/ARCHITECTURE.md` — design model and integration architecture
- `docs/IMPLEMENTATION_PLAN.md` — staged build plan
- `docs/CONFIG_EXAMPLES.md` — target YAML and automation examples

## Current recommendation

Stages 1-3 have already been implemented once. Before continuing to schedule/due/overdue logic, ask Codex to perform **Stage 3A**.

Stage 3A changes the recommended completion model from:

```yaml
service: tracked_tasks.mark_done
data:
  task_id: bins
```

to the more Home Assistant-native:

```yaml
service: button.press
target:
  entity_id: button.bins_mark_done
```

The task still appears as a device. Its sensors expose task state, and its button entity acts like the task's `mark_done` method.

## Recommended next steps

1. Paste `CODEX_PROMPT.md` into Codex against the existing Stage 1-3 implementation.
2. Test that `button.press` against `button.bins_mark_done` updates the task state.
3. Only then move on to Stage 4 schedule calculation.

Do not ask Codex to implement Stage 4+ until Stage 3A is tested.
