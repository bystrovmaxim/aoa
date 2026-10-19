"""
# 05_aspect_declarations.py — The four declarations, and what they refuse

The machine calls four kinds of method itself: the regular aspect, the summary, the
error handler and the compensator. It hands each of them a fixed set of values, in a
fixed order, and reads one answer back. So the signature of those methods is not the
author's private business — it is the contract.

This example declares one mistake at a time and prints what the framework says. Every
refusal below arrives **before the run**: either while the class body executes (the
shape), or while the capability is assembled (the types). Nothing here is discovered by
calling the operation and reading its output.

What's new:
  - the order the pipeline passes: self, params, state, box, connections (+ error, + ctx)
  - two moments: the shape is checked where the method is written, the types when the
    operation's own Params and Result exist
  - AspectSignatureError, DuplicateSummaryAspectError, ActionResultTypeError

Run:
    uv run python examples/step_01_Action_and_pipeline/05_aspect_declarations.py
"""

import asyncio
from typing import Any

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import (
    ActionResultTypeError,
    AspectSignatureError,
    DuplicateSummaryAspectError,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, ParamsStub, ResultStub
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.resources import Connections


# %% Setup
class DeclarationsDomain(BaseDomain):
    """Group the declaration cases."""

    name = "declarations"
    description = "What an aspect declaration must be"


def report(case: str, outcome: str) -> None:
    """Print one case and what the framework answered, without the moment sentence."""
    head = outcome.split(" Refused while")[0].strip()
    print(f"{case:<26} {head}")


# %% Case 1 — a renamed parameter, refused where the method is written
# The pipeline passes params, state, box, connections. This method says `p` and `s`.
# It would run: Python binds by position, so `p` would receive the parameters object.
#
# expected-refusal: AspectSignatureError — every case below is wrong on purpose
try:

    @summary_aspect("Renamed parameters")
    async def renamed_summary(self, p: ParamsStub, s: Any, box: Any, connections: Any) -> ResultStub:
        return ResultStub()

except AspectSignatureError as error:
    report("renamed parameter", str(error))


# %% Case 2 — a signature the pipeline cannot call
# Keyword-only parameters cannot receive values the pipeline passes by position.
#
# expected-refusal: AspectSignatureError
try:

    @regular_aspect("Keyword-only parameters")
    async def keyword_only_aspect(
        self, params: ParamsStub, state: Any, box: Any, *, connections: Any
    ) -> dict[str, Any]:
        return {}

except AspectSignatureError as error:
    report("keyword-only parameter", str(error))


# %% Case 3 — an untyped declaration
# The annotations are how a step states what it receives; a bare one is refused.
#
# expected-refusal: AspectSignatureError
try:

    @summary_aspect("No annotations")
    async def untyped_summary(self, params, state, box, connections) -> ResultStub:
        return ResultStub()

except AspectSignatureError as error:
    report("untyped declaration", str(error))


# %% Case 4 — a type the pipeline never hands over, refused at assembly
# The shape is right here; only the `box` annotation is wrong, and that is visible
# only once the operation's own names exist.
# expected-refusal: AspectSignatureError — the shape is right, only the type is wrong
@exclude_graph_model
@meta(description="declarations: a box that is not a tool box", domain=DeclarationsDomain)
@check_roles(GuestRole)
class MistypedAction(BaseAction[ParamsStub, ResultStub]):
    """An operation whose summary promises the wrong type for the tool box."""

    @summary_aspect("Wrong box type")
    async def mistyped_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: str,
        connections: Connections,
    ) -> ResultStub:
        """Assemble the result."""
        return ResultStub()


try:
    ActionGraphNode(MistypedAction)
except AspectSignatureError as error:
    report("wrong parameter type", str(error))


# %% Case 5 — two summaries, refused as two summaries
# An operation answers once. The refusal names both methods instead of pointing at a
# graph node that was never written.
#
# expected-refusal: DuplicateSummaryAspectError
@exclude_graph_model
@meta(description="declarations: two exit points", domain=DeclarationsDomain)
@check_roles(GuestRole)
class TwoSummariesAction(BaseAction[ParamsStub, ResultStub]):
    """An operation that declares two summary aspects."""

    @summary_aspect("First exit point")
    async def first_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ResultStub:
        """Assemble the result, first way."""
        return ResultStub()

    @summary_aspect("Second exit point")
    async def second_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ResultStub:
        """Assemble the result, second way."""
        return ResultStub()


try:
    ActionGraphNode(TwoSummariesAction)
except DuplicateSummaryAspectError as error:
    report("two summaries", str(error))


# %% Case 6 — the answer is not the operation's Result
# The annotation is honest; the returned value is not. Only the run can see that.
#
# expected-refusal: ActionResultTypeError
@meta(description="declarations: an answer that is not a Result", domain=DeclarationsDomain)
@check_roles(GuestRole)
class WrongAnswerAction(BaseAction[ParamsStub, ResultStub]):
    """An operation whose summary returns a mapping instead of its Result."""

    @summary_aspect("Answer with a mapping")
    async def wrong_answer_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ResultStub:
        """Return something that is not the declared Result."""
        return {"not": "a result"}  # type: ignore[return-value]


async def run_wrong_answer() -> None:
    """Run the operation and report what the machine says about its answer."""
    try:
        await ActionProductMachine(cache_coordinator=None).run(Context(), WrongAnswerAction(), ParamsStub())
    except ActionResultTypeError as error:
        report("answer is not a Result", str(error))


# %% Case 7 — a declaration that complies, and runs
@meta(description="declarations: the contract, met", domain=DeclarationsDomain)
@check_roles(GuestRole)
class CorrectAction(BaseAction[ParamsStub, ResultStub]):
    """An operation whose declaration is the contract."""

    @summary_aspect("Assemble the result")
    async def correct_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ResultStub:
        """Build the empty result."""
        return ResultStub()


async def main() -> None:
    """Run the seventh case; the first six reported as they were declared."""
    answer = await ActionProductMachine(cache_coordinator=None).run(Context(), CorrectAction(), ParamsStub())
    report("a correct declaration", f"ran, answer: {type(answer).__name__}")
    await run_wrong_answer()


asyncio.run(main())
