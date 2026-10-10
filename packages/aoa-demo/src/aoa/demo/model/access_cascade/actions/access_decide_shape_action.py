# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/access_decide_shape_action.py
"""
AccessDecideShapeAction — the operation with a declared object rule.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-006): the diagram must show an operation with a
declared object rule — a rule answered on a real object inside the run,
distinct from the role checks. The rule always allows; the declaration is
the shape being drawn, not the decision itself.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @access_decide(...)  →  one @access_decide edge into an AccessDecideGraphNode
    summary aspect       →  empty Result
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


@meta(
    description="Shape: a declared object rule answered on a real object",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class AccessDecideShapeAction(
    BaseAction["AccessDecideShapeAction.Params", "AccessDecideShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose access carries a declared object rule.
    CONTRACT: One ``@access_decide`` declaration answered on a real object inside the run.
    INVARIANTS: No business meaning; the declaration is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the access-decide drawing fixture."""

    class Result(BaseResult):
        """Empty result for the access-decide drawing fixture."""

    @access_decide("Answer the declared object rule for the drawing fixture")
    async def answer_on_object_access_decide(
        self,
        params: AccessDecideShapeAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """The fixture always allows; the declaration is the shape being drawn."""
        _ = (params, box, connections)
        return Allowed()

    @summary_aspect("Return the empty result")
    async def object_rule_summary(
        self,
        params: AccessDecideShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AccessDecideShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return AccessDecideShapeAction.Result()
