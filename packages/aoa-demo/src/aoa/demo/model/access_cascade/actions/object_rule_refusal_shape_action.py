# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/object_rule_refusal_shape_action.py
"""
ObjectRuleRefusalShapeAction — the operation whose object rule refuses with the author's reason.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-004): the diagram must show an operation whose object rule
answers ``Refused("REASON")`` — the author's own reason — although the role gate
let the caller through. The rule always refuses; the refusal is the shape, and
there is no business logic behind it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @access_decide(...)  →  one @access_decide edge into an AccessDecideGraphNode
    summary aspect       →  empty Result
"""

from __future__ import annotations

from aoa.action_machine.intents.access_control import Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.access_cascade.roles import CascadeOfficerRole

_REFUSAL_REASON = "shape: the object rule refuses with the author's own reason"


@meta(
    description="Shape: the object rule refuses with the author's own reason",
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class ObjectRuleRefusalShapeAction(
    BaseAction["ObjectRuleRefusalShapeAction.Params", "ObjectRuleRefusalShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose object rule refuses with the author's own reason.
    CONTRACT: One ``@access_decide`` declaration returning ``Refused`` with a declared reason.
    INVARIANTS: No business meaning; the refusing object rule is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the object-rule-refusal drawing fixture."""

    class Result(BaseResult):
        """Empty result for the object-rule-refusal drawing fixture."""

    @access_decide("Refuse with the author's own reason")
    async def object_rule_refusal_access_decide(
        self,
        params: ObjectRuleRefusalShapeAction.Params,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """The fixture always refuses, with the author's reason."""
        _ = (params, box, connections)
        return Refused(_REFUSAL_REASON)

    @summary_aspect("Return the empty result")
    async def object_rule_refusal_summary(
        self,
        params: ObjectRuleRefusalShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ObjectRuleRefusalShapeAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return ObjectRuleRefusalShapeAction.Result()
