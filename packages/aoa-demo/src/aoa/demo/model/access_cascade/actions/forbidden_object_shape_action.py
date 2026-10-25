# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/forbidden_object_shape_action.py
"""
ForbiddenObjectShapeAction — the operation whose object rule refuses every caller alike.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-005): the diagram must show an operation whose object rule
answers the shared ``FORBIDDEN_OBJECT`` — "no such object" and "not yours" are
deliberately the same answer — for everyone alike. The rule always refuses with
the shared answer; there is no business logic behind it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @access_decide(...)  →  one @access_decide edge returning FORBIDDEN_OBJECT
    summary aspect       →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeOfficerRole


@meta(
    description="Shape: the object rule refuses every caller with the shared answer",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class ForbiddenObjectShapeAction(
    BaseAction["ForbiddenObjectShapeAction.Params", "ForbiddenObjectShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose object rule refuses every caller with the shared answer.
    CONTRACT: One ``@access_decide`` declaration returning ``FORBIDDEN_OBJECT``.
    INVARIANTS: No business meaning; the shared refusal is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the forbidden-object drawing fixture."""

    class Result(BaseResult):
        """Empty result for the forbidden-object drawing fixture."""

    @access_decide("Refuse every caller with the shared object answer")
    async def forbidden_object_access_decide(
        self,
        params: ForbiddenObjectShapeAction.Params,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """The fixture always refuses with the shared answer."""
        _ = (params, box, connections)
        return FORBIDDEN_OBJECT

    @summary_aspect("Return the empty result")
    async def forbidden_object_summary(
        self,
        params: ForbiddenObjectShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ForbiddenObjectShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return ForbiddenObjectShapeAction.Result()
