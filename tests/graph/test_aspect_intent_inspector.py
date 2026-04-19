# tests/graph/test_aspect_intent_inspector.py
"""Unit tests for AspectIntentInspector."""

from __future__ import annotations

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.legacy.aspect_intent import AspectIntent
from action_machine.legacy.aspect_intent_inspector import AspectIntentInspector
from action_machine.legacy.interchange_vertex_labels import (
    REGULAR_ASPECT_VERTEX_TYPE,
    SUMMARY_ASPECT_VERTEX_TYPE,
)
from graph.base_intent_inspector import BaseIntentInspector


class _NoAspectAction(AspectIntent):
    pass


class _AspectAction(AspectIntent):
    @regular_aspect("Step")
    async def run_step_aspect(self, params, state, box, connections):
        return {}

    @summary_aspect("Summary")
    @context_requires(Ctx.User.user_id)
    async def build_result_summary(self, params, state, box, connections, ctx):
        return {}


def test_aspect_inspector_returns_none_without_aspects() -> None:
    assert AspectIntentInspector.inspect(_NoAspectAction) is None


def test_aspect_inspector_builds_payload_with_aspect_entries() -> None:
    raw = AspectIntentInspector.inspect(_AspectAction)
    assert isinstance(raw, list)
    assert len(raw) == 3
    aspect_payloads = [
        p
        for p in raw
        if p.node_type in (REGULAR_ASPECT_VERTEX_TYPE, SUMMARY_ASPECT_VERTEX_TYPE)
    ]
    action_payloads = [p for p in raw if p.node_type == "Action"]
    assert len(aspect_payloads) == 2
    assert len(action_payloads) == 1
    ap0 = action_payloads[0]
    assert ap0.node_class is _AspectAction
    assert ap0.node_name == BaseIntentInspector._make_node_name(_AspectAction)
    assert len(ap0.edges) == 2
    assert {e.edge_type for e in ap0.edges} == {"has_aspect"}
    assert {e.target_node_type for e in ap0.edges} == {
        REGULAR_ASPECT_VERTEX_TYPE,
        SUMMARY_ASPECT_VERTEX_TYPE,
    }

    by_method: dict[str, object] = {}
    for p in aspect_payloads:
        rows = dict(p.node_meta)["aspects"]
        assert len(rows) == 1
        row0 = dict(rows[0])
        by_method[row0["method_name"]] = p
    assert "run_step_aspect" in by_method
    assert "build_result_summary" in by_method

    summary_rows = dict(by_method["build_result_summary"].node_meta)["aspects"]
    assert len(summary_rows) == 1
    sd = dict(summary_rows[0])
    assert sd["aspect_type"] == "summary"
    assert "user.user_id" in sd["context_keys"]
