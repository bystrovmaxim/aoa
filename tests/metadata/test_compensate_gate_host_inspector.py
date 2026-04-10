# tests/metadata/test_compensate_gate_host_inspector.py
"""Unit tests for CompensateGateHostInspector."""

from __future__ import annotations

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.compensate.compensate_decorator import compensate
from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx


class _NoCompensateAction(AspectGateHost):
    pass


class _CompensateAction(AspectGateHost):
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
    assert CompensateGateHostInspector.inspect(_NoCompensateAction) is None


def test_compensate_inspector_builds_payload_with_compensator_entries() -> None:
    payload = CompensateGateHostInspector.inspect(_CompensateAction)
    assert payload is not None
    assert payload.node_type == "compensator"

    data = dict(payload.node_meta)
    compensators = data["compensators"]
    assert len(compensators) == 2

    names = {entry[0] for entry in compensators}
    assert "rollback_pay_compensate" in names
    assert "rollback_reserve_compensate" in names

    reserve = next(entry for entry in compensators if entry[0] == "rollback_reserve_compensate")
    assert reserve[1] == "reserve_aspect"
    assert reserve[2] == "Rollback reservation"
    assert "user.user_id" in reserve[4]
