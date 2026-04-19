# tests/graph/test_compensate_intent_inspector.py
"""Unit tests for CompensateIntentInspector."""

from __future__ import annotations

from action_machine.context.ctx_constants import Ctx
from action_machine.graph import graph_builder as graph_builder_mod
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.legacy.aspect_intent import AspectIntent
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
    hydrate_compensator_row,
)
from action_machine.legacy.interchange_vertex_labels import COMPENSATOR_VERTEX_TYPE


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
    produced = CompensateIntentInspector.inspect(_CompensateAction)
    assert isinstance(produced, list)
    comp_payloads = [p for p in produced if p.node_type == COMPENSATOR_VERTEX_TYPE]
    action_payloads = [p for p in produced if p.node_type == "Action"]
    assert len(comp_payloads) == 2
    assert len(action_payloads) == 1
    act = action_payloads[0]
    assert {e.edge_type for e in act.edges} == {"has_compensator"}
    assert len(act.edges) == 2

    names = {hydrate_compensator_row(p.node_meta).method_name for p in comp_payloads}
    assert names == {"rollback_pay_compensate", "rollback_reserve_compensate"}

    reserve_p = next(p for p in comp_payloads if "rollback_reserve" in p.node_name)
    reserve = hydrate_compensator_row(reserve_p.node_meta)
    assert reserve.target_aspect_name == "reserve_aspect"
    assert reserve.description == "Rollback reservation"
    assert "user.user_id" in reserve.context_keys
    assert graph_builder_mod._facet_vertex_label(reserve_p) == "rollback_reserve_compensate"
