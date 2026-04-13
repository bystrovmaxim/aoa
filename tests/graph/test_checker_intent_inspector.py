# tests/graph/test_checker_intent_inspector.py
"""Unit tests for CheckerIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.checker_intent_inspector import CheckerIntentInspector
from action_machine.intents.checkers.checker_intent import CheckerIntent
from action_machine.intents.checkers.result_string_checker import result_string


class _NoCheckerAction(CheckerIntent):
    pass


class _CheckerAction(CheckerIntent):
    @result_string("name", required=True, min_length=2)
    async def validate_name_aspect(self, params, state, box, connections):
        return {"name": "ok"}


def test_checker_inspector_returns_none_without_checkers() -> None:
    assert CheckerIntentInspector.inspect(_NoCheckerAction) is None


def test_checker_inspector_builds_payload_with_checker_entries() -> None:
    payload = CheckerIntentInspector.inspect(_CheckerAction)
    assert payload is not None
    assert payload.node_type == "checker"

    data = dict(payload.node_meta)
    checkers = data["checkers"]
    assert len(checkers) == 1

    row = dict(checkers[0])
    assert row["method_name"] == "validate_name_aspect"
    assert row["checker_class"] is not None
    assert row["field_name"] == "name"
    assert row["required"] is True
    assert ("min_length", 2) in row["extra_params"]
