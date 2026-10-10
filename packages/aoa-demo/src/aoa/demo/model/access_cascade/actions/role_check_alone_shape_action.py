# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/role_check_alone_shape_action.py
"""
RoleCheckAloneShapeAction — the operation whose access is a role check alone.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-003): the diagram must show an operation whose access
is decided by a single matching role and nothing else — no condition, no
guard, no object rule. The class carries no business meaning.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(CascadeOfficerRole)  →  one RoleGraphEdge, no when, no guard
    summary aspect                    →  empty Result (the fixture does no work)
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


@meta(
    description="Shape: access decided by a role check alone",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class RoleCheckAloneShapeAction(
    BaseAction["RoleCheckAloneShapeAction.Params", "RoleCheckAloneShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose access is one role check and nothing else.
    CONTRACT: The declared access is a single role, with no condition, guard or object rule.
    INVARIANTS: No business meaning; the declaration is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the role-check-alone drawing fixture."""

    class Result(BaseResult):
        """Empty result for the role-check-alone drawing fixture."""

    @summary_aspect("Return the empty result")
    async def role_check_summary(
        self,
        params: "RoleCheckAloneShapeAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "RoleCheckAloneShapeAction.Result":
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return RoleCheckAloneShapeAction.Result()
