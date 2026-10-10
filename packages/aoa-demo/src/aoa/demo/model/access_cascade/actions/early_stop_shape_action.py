# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/early_stop_shape_action.py
"""
EarlyStopShapeAction — the operation whose cascade provably stops at the first gate.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-008): the diagram shows the full declared cascade — a
role check plus a declared object rule — while the runnable test proves that
a caller refused at the role gate never reaches the object rule. The proof
instrument is the module-level probe counter below, which the object rule
increments when it runs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    machine.run(stranger)
        →  CHECK_ROLES refuses          (AccessDenied, gate="CHECK_ROLES")
        →  object rule never runs       (_PROBE_CALLS stays 0)
"""

from __future__ import annotations

from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeOfficerRole

_PROBE_CALLS = 0
"""Probe counter: how many times the declared object rule ran (reset by the tests)."""


@meta(
    description="Shape: the cascade stops early — the later stages are provably not reached",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class EarlyStopShapeAction(
    BaseAction["EarlyStopShapeAction.Params", "EarlyStopShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose cascade stops at the first refusing gate.
    CONTRACT: A role check plus a declared object rule that increments the probe.
    INVARIANTS: No business meaning; the early stop is the shape being proven.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the early-stop drawing fixture."""

    class Result(BaseResult):
        """Empty result for the early-stop drawing fixture."""

    @access_decide("Count the probe and allow — the early stop is proven by the tests")
    async def probe_then_allow_access_decide(
        self,
        params: "EarlyStopShapeAction.Params",
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Increment the probe counter, then allow."""
        global _PROBE_CALLS
        _ = (params, box, connections)
        _PROBE_CALLS += 1
        return Allowed()

    @summary_aspect("Return the empty result")
    async def early_stop_summary(
        self,
        params: "EarlyStopShapeAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "EarlyStopShapeAction.Result":
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return EarlyStopShapeAction.Result()
