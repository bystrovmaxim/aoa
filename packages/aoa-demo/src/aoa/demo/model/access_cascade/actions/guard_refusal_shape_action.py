# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/guard_refusal_shape_action.py
"""
GuardRefusalShapeAction — the operation whose shared guard refuses every caller alike.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-005): the diagram must show an operation whose shared
guard refuses for everyone alike — one limit for all callers, distinct from a
role's own condition. The guard is a constant ``False`` with a declared
reason; there is no business logic behind it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(role, guard=..., guard_reason=...)  →  ActionGraphNode with ``guard``
    summary aspect                                   →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeOfficerRole

_GUARD_REASON = "shape: GUARD refuses every caller alike"


@meta(
    description="Shape: the shared guard refuses every caller alike",
    domain=AccessCascadeDomain,
)
@check_roles(
    CascadeOfficerRole,
    guard=lambda *_: False,
    guard_reason=_GUARD_REASON,
)
class GuardRefusalShapeAction(
    BaseAction["GuardRefusalShapeAction.Params", "GuardRefusalShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose shared guard refuses for everyone alike.
    CONTRACT: One role plus a synchronous ``guard`` returning ``False`` and a declared reason.
    INVARIANTS: No business meaning; the shared guard is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the guard-refusal drawing fixture."""

    class Result(BaseResult):
        """Empty result for the guard-refusal drawing fixture."""

    @summary_aspect("Return the empty result")
    async def guard_refusal_summary(
        self,
        params: "GuardRefusalShapeAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "GuardRefusalShapeAction.Result":
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return GuardRefusalShapeAction.Result()
