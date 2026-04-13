# tests/metadata/test_aspect_intent_inspector.py
"""Unit tests for AspectIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.aspect_intent_inspector import AspectIntentInspector
from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx


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
    payload = AspectIntentInspector.inspect(_AspectAction)
    assert payload is not None
    assert payload.node_type == "aspect"
    data = dict(payload.node_meta)
    aspects = data["aspects"]
    assert len(aspects) == 2

    names = {dict(entry)["method_name"] for entry in aspects}
    assert "run_step_aspect" in names
    assert "build_result_summary" in names

    summary = next(e for e in aspects if dict(e)["method_name"] == "build_result_summary")
    sd = dict(summary)
    assert sd["aspect_type"] == "summary"
    assert "user.user_id" in sd["context_keys"]
