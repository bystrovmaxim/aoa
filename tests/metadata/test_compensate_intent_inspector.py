# tests/metadata/test_compensate_intent_inspector.py
"""Unit tests for CompensateIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx


class _NoCompensateAction(AspectIntent):
    pass


class _CompensateAction(AspectIntent):
    @compensate("pay_aspect", "Rollback payment")
    async def rollback_pay_compensate(
        self, params, state_before, state_after, box, connections, error
    ):
        return None

    @compensate("reserve_aspect", "Rollback reservation")
    @context_requires(Ctx.User.user_id)
    async def rollback_reserve_compensate(
        self, params, state_before, state_after, box, connections, error, ctx
    ):
        return {"ctx": bool(ctx)}


def test_compensate_inspector_returns_none_without_compensators() -> None:
    assert CompensateIntentInspector.inspect(_NoCompensateAction) is None


def test_compensate_inspector_builds_payload_with_compensator_entries() -> None:
    payload = CompensateIntentInspector.inspect(_CompensateAction)
    assert payload is not None
    assert payload.node_type == "compensator"

    data = dict(payload.node_meta)
    compensators = data["compensators"]
    assert len(compensators) == 2

    names = {dict(entry)["method_name"] for entry in compensators}
    assert "rollback_pay_compensate" in names
    assert "rollback_reserve_compensate" in names

    reserve = next(
        e for e in compensators
        if dict(e)["method_name"] == "rollback_reserve_compensate"
    )
    rd = dict(reserve)
    assert rd["target_aspect_name"] == "reserve_aspect"
    assert rd["description"] == "Rollback reservation"
    assert "user.user_id" in rd["context_keys"]
