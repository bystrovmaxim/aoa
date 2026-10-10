# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/system_role_edge_shape_action.py
"""
SystemRoleEdgeShapeAction — the operation that draws the system-level role branch.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-001): the use-case diagram pulls roles into its closure
only through ``@check_roles`` edges, so the system-level branch needs an
operation that names it. This fixture provides exactly that edge; it carries
no business meaning.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(CascadeSystemGateRole)  →  one RoleGraphEdge into the system branch
    summary aspect                       →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeSystemGateRole


@meta(
    description="Shape: the system-level role branch, drawn through this role edge",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeSystemGateRole)
class SystemRoleEdgeShapeAction(
    BaseAction["SystemRoleEdgeShapeAction.Params", "SystemRoleEdgeShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose single role edge makes the system branch visible.
    CONTRACT: One grant naming ``CascadeSystemGateRole``.
    INVARIANTS: No business meaning; the system-branch edge is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the system-role-edge drawing fixture."""

    class Result(BaseResult):
        """Empty result for the system-role-edge drawing fixture."""

    @summary_aspect("Return the empty result")
    async def system_role_edge_summary(
        self,
        params: SystemRoleEdgeShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> SystemRoleEdgeShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return SystemRoleEdgeShapeAction.Result()
