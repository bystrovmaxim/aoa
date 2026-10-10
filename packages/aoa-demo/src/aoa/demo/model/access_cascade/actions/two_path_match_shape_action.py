# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/two_path_match_shape_action.py
"""
TwoPathMatchShapeAction — the operation two roles match through different paths.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-007): the diagram must show one operation reached by
two roles through different branches — one match through the application
chain, one through the domain branch. The class carries no business meaning.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)
        →  two RoleGraphEdges into one action node
    summary aspect  →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeDomainSpecialistRole, CascadeTraineeRole


@meta(
    description="Shape: two roles match one operation through different paths",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)
class TwoPathMatchShapeAction(
    BaseAction["TwoPathMatchShapeAction.Params", "TwoPathMatchShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture matched by two roles from different branches.
    CONTRACT: Two grants, one from the application chain and one from the domain branch.
    INVARIANTS: No business meaning; the two matching paths are the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the two-path-match drawing fixture."""

    class Result(BaseResult):
        """Empty result for the two-path-match drawing fixture."""

    @summary_aspect("Return the empty result")
    async def two_path_summary(
        self,
        params: TwoPathMatchShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> TwoPathMatchShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return TwoPathMatchShapeAction.Result()
