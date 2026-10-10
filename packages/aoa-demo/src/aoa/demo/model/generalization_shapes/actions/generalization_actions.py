# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/actions/generalization_actions.py
"""
Generalization action fixtures — one parent, two children, inheritance edges.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The three actions exist so the use-case diagram draws generalization: two
children subclass one parent, each subclassing producing a ``parent_action``
inheritance edge. None of the names is a business duty.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GeneralizationParentAction
        ├── GeneralizationFirstChildAction   →  parent_action edge into the parent
        └── GeneralizationSecondChildAction   →  parent_action edge into the parent
"""

from __future__ import annotations

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from aoa.demo.model.generalization_shapes.generalization_shapes_domain import GeneralizationShapesDomain


@meta(
    description="Shape: the parent end of a parent_action generalization edge",
    domain=GeneralizationShapesDomain,
)
@check_roles(GuestRole)
class GeneralizationParentAction(
    BaseAction["GeneralizationParentAction.Params", "GeneralizationParentAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose children produce the parent_action edges.
    CONTRACT: A plain action; the generalization shape comes from its subclasses.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the parent drawing fixture."""

    class Result(BaseResult):
        """Empty result for the parent drawing fixture."""

    @summary_aspect("Return the empty result")
    async def parent_generalization_summary(
        self,
        params: GeneralizationParentAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GeneralizationParentAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return GeneralizationParentAction.Result()


@meta(
    description="Shape: a child action — the diagram draws a parent_action arrow into the parent",
    domain=GeneralizationShapesDomain,
)
@check_roles(GuestRole)
class GeneralizationFirstChildAction(GeneralizationParentAction):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture child; its subclassing is the drawn inheritance edge.
    CONTRACT: Subclasses ``GeneralizationParentAction`` and nothing else changes.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the child drawing fixture."""

    class Result(BaseResult):
        """Empty result for the child drawing fixture."""

    @summary_aspect("Return the empty result")
    async def child_a_summary(
        self,
        params: GeneralizationFirstChildAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GeneralizationFirstChildAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return GeneralizationFirstChildAction.Result()


@meta(
    description="Shape: a second child action — the diagram draws another parent_action arrow into the parent",
    domain=GeneralizationShapesDomain,
)
@check_roles(GuestRole)
class GeneralizationSecondChildAction(GeneralizationParentAction):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture child; its subclassing is the drawn inheritance edge.
    CONTRACT: Subclasses ``GeneralizationParentAction`` and nothing else changes.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the child drawing fixture."""

    class Result(BaseResult):
        """Empty result for the child drawing fixture."""

    @summary_aspect("Return the empty result")
    async def child_b_summary(
        self,
        params: GeneralizationSecondChildAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GeneralizationSecondChildAction.Result:
        """Build the empty fixture result."""
        _ = (params, state, box, connections)
        return GeneralizationSecondChildAction.Result()
