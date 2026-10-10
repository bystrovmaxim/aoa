# packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/question_path_shape_action.py
"""
QuestionPathShapeAction — the asked-about operation whose refusal is an answer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-009), present twice. First, the drawing: the
description below is the label Maxitor shows for the asked-about operation.
Second, the proof: the runnable test asks ``machine.check_access_decide`` in
advance and receives a refusal as an answer — never an exception — while the
pipeline probe below proves no aspect ran.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    machine.check_access_decide(stranger, QuestionPathShapeAction)
        →  Refused(gate="CHECK_ROLES") — an answer, not an exception
        →  _PIPELINE_RUNS stays 0          (no aspect ran)
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

_PIPELINE_RUNS: dict[str, int] = {"count": 0}
"""Pipeline probe: how many times the summary aspect ran (reset by the tests)."""

_QUESTION_LABEL = "Shape: the asked-about operation — the refusal returns as an answer, never an exception"


@meta(
    description=_QUESTION_LABEL,
    domain=AccessCascadeDomain,
)
@check_roles(CascadeOfficerRole)
class QuestionPathShapeAction(
    BaseAction["QuestionPathShapeAction.Params", "QuestionPathShapeAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose refusal is asked for in advance and returned as an answer.
    CONTRACT: A role check plus a declared object rule; the description is the drawn label.
    INVARIANTS: No business meaning; the answer-not-exception property is the shape being proven.
    AI-CORE-END
    """

    class Params(BaseParams):
        """Empty input for the question-path drawing fixture."""

    class Result(BaseResult):
        """Empty result for the question-path drawing fixture."""

    @access_decide("Answer the declared object rule for the asked-about fixture")
    async def answer_for_question_access_decide(
        self,
        params: QuestionPathShapeAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """The fixture always allows; the question path is the shape being proven."""
        _ = (params, box, connections)
        return Allowed()

    @summary_aspect("Return the empty result")
    async def question_path_summary(
        self,
        params: QuestionPathShapeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> QuestionPathShapeAction.Result:
        """Count the pipeline probe and build the empty fixture result."""
        _ = (params, state, box, connections)
        _PIPELINE_RUNS["count"] += 1
        return QuestionPathShapeAction.Result()
