# tests/graph/test_checker_intent_inspector.py
"""Unit tests for CheckerIntentInspector."""

from __future__ import annotations

from action_machine.graph import graph_builder as graph_builder_mod
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.legacy.aspect_intent import AspectIntent
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.checkers.checker_intent import CheckerIntent
from action_machine.intents.checkers.checker_intent_inspector import CheckerIntentInspector
from action_machine.intents.checkers.result_string_checker import result_string
from action_machine.legacy.interchange_vertex_labels import CHECKER_VERTEX_TYPE


class _NoCheckerAction(CheckerIntent, AspectIntent):
    pass


class _CheckerAction(CheckerIntent, AspectIntent):
    @regular_aspect("Validate name")
    @result_string("name", required=True, min_length=2)
    async def validate_name_aspect(self, params, state, box, connections):
        return {"name": "ok"}


def test_checker_inspector_returns_none_without_checkers() -> None:
    assert CheckerIntentInspector.inspect(_NoCheckerAction) is None


def test_checker_inspector_builds_payload_with_checker_entries() -> None:
    raw = CheckerIntentInspector.inspect(_CheckerAction)
    assert isinstance(raw, list)
    assert len(raw) == 1
    payload = raw[0]
    assert payload.node_type == CHECKER_VERTEX_TYPE
    host = BaseIntentInspector._make_node_name(_CheckerAction)
    assert payload.node_name == f"{host}:validate_name_aspect:ResultStringChecker:name"
    assert len(payload.edges) == 1
    assert payload.edges[0].edge_type == "checks_aspect"
    assert payload.edges[0].target_name == f"{host}:validate_name_aspect"

    row = dict(payload.node_meta)
    assert row["method_name"] == "validate_name_aspect"
    assert row["checker_class"] is not None
    assert row["field_name"] == "name"
    assert row["required"] is True
    assert ("min_length", 2) in row["extra_params"]
    assert graph_builder_mod._facet_vertex_label(payload) == "name"
