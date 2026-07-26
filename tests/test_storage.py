"""Tests for tracked task storage serialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
STORAGE_PATH = ROOT / "custom_components" / "tracked_tasks" / "storage.py"
SPEC = importlib.util.spec_from_file_location("tracked_tasks_storage", STORAGE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
storage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = storage
SPEC.loader.exec_module(storage)

UTC = timezone.utc


@dataclass
class State:
    """Small state test double."""

    last_completed: datetime | None = None
    completed_due_at: datetime | None = None


class TestStorageDeserialization(unittest.TestCase):
    """Storage restore behavior."""

    def test_missing_storage_restores_no_states(self) -> None:
        states = storage.deserialize_task_states(None, ["bins"], State)

        self.assertEqual(states, {})

    def test_invalid_storage_root_restores_no_states(self) -> None:
        states = storage.deserialize_task_states(["not", "a", "dict"], ["bins"], State)

        self.assertEqual(states, {})

    def test_restores_known_task_datetimes(self) -> None:
        states = storage.deserialize_task_states(
            {
                "version": 1,
                "tasks": {
                    "bins": {
                        "last_completed": "2026-07-23T20:10:00+00:00",
                        "completed_due_at": "2026-07-23T20:00:00+00:00",
                    },
                    "unknown": {
                        "last_completed": "2026-07-23T21:10:00+00:00",
                        "completed_due_at": "2026-07-23T21:00:00+00:00",
                    },
                },
            },
            ["bins"],
            State,
        )

        self.assertEqual(
            states["bins"].last_completed,
            datetime(2026, 7, 23, 20, 10, tzinfo=UTC),
        )
        self.assertEqual(
            states["bins"].completed_due_at,
            datetime(2026, 7, 23, 20, 0, tzinfo=UTC),
        )
        self.assertNotIn("unknown", states)

    def test_corrupt_task_datetime_restores_empty_state(self) -> None:
        states = storage.deserialize_task_states(
            {
                "version": 1,
                "tasks": {
                    "bins": {
                        "last_completed": "not-a-datetime",
                        "completed_due_at": 123,
                    },
                },
            },
            ["bins"],
            State,
        )

        self.assertIsNone(states["bins"].last_completed)
        self.assertIsNone(states["bins"].completed_due_at)

    def test_simple_legacy_task_mapping_is_accepted(self) -> None:
        states = storage.deserialize_task_states(
            {
                "bins": {
                    "last_completed": "2026-07-23T20:10:00+00:00",
                    "completed_due_at": "2026-07-23T20:00:00+00:00",
                },
            },
            ["bins"],
            State,
        )

        self.assertEqual(
            states["bins"].completed_due_at,
            datetime(2026, 7, 23, 20, 0, tzinfo=UTC),
        )


if __name__ == "__main__":
    unittest.main()
