# Tracked Tasks Codex Handoff

This folder contains handoff material for Codex to build a custom Home Assistant integration called `tracked_tasks`.

## Files

- `AGENTS.md` — main project instructions and constraints for Codex
- `CODEX_PROMPT.md` — initial prompt to paste into Codex
- `docs/ARCHITECTURE.md` — design model and integration architecture
- `docs/IMPLEMENTATION_PLAN.md` — staged build plan
- `docs/CONFIG_EXAMPLES.md` — target YAML and automation examples

## Recommended approach

Ask Codex to implement Stages 1–3 first:

1. Integration skeleton
2. Status and last-completed entities
3. `mark_done` service/action and dashboard button

Then test in Home Assistant before asking Codex to continue with schedule, due, overdue, next due, time remaining, persistence, and recurrence support.
