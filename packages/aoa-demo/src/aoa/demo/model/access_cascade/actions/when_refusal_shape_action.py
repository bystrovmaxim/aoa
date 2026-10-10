# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/when_refusal_shape_action.py
"""
WhenRefusalShapeAction — the operation whose matched role refuses on its own condition.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-004): the diagram must show an operation whose role
carries a condition that can refuse although the role itself matched. The
condition is a constant ``False`` with a declared reason — the refusal is the
shape, and there is no business logic behind it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    grant(CascadeOfficerRole, when=..., reason=...)  →  RoleGraphEdge with ``when``
    summary aspect                                   →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeOfficerRole

_WHEN_REASON = "shape: WHEN refuses although the role matched"


@meta(
    description="Shape: a role condition refuses although the role matched",
    domain=AccessCascadeDomain,
)
@check_roles(
    grant(
        CascadeOfficerRole,
        when=lambda *_: False,
        reason=_WHEN_REASON,
    ),
)
class WhenRefusalShapeAction(
    BaseAction["WhenRefusalShapeAction.Params", "WhenRefusalShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose role carries a refusing condition.
    CONTRACT: One grant with a synchronous ``when`` returning ``False`` and a declared reason.
    INVARIANTS: No business meaning; the refusing condition is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the when-refusal drawing fixture."""

    class Result(BaseResult):
        """Empty result for the when-refusal drawing fixture."""

    @summary_aspect("Return the empty result")
    async def when_refusal_summary(
        self,
        params: WhenRefusalShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> WhenRefusalShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return WhenRefusalShapeAction.Result()
