# packages/aoa-action-machine/tests/action_machine/runtime/test_every_method_has_its_own_box.py
"""
Every method of an action gets its own box — what each kind's log sees (issue #331).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The tests of one kind's ``state`` and behaviour come first. The method name is asserted
only by the rule's test, so that taking one kind's name away fails that test alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.ctx_constants import Ctx
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied, AccessUndecided
from aoa.action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from aoa.action_machine.graph.nodes.access_decide_graph_node import AccessDecideGraphNode
from aoa.action_machine.graph.nodes.compensator_graph_node import CompensatorGraphNode
from aoa.action_machine.graph.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from aoa.action_machine.graph.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from aoa.action_machine.graph.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Gate, Refused, Undecided, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import OrdersDomain, SystemDomain
from ...support.domain_model.services import PaymentServiceResource


@dataclass(frozen=True)
class _Line:
    """One written log line, with what the logger received beside it."""

    action: str
    method: str
    state: dict[str, Any]
    message: str
    nest_level: int


class _RecordingLogger(BaseLogger):
    """A logger keeping every line of the run."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[_Line] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """Keep one line."""
        self.lines.append(_Line(scope.action, scope.aspect, state.to_dict(), message, scope.nest_level))


class _FailParams(BaseParams):
    """Says where the run fails."""

    fail_in: str = Field(default="", description="The step that raises")


class _OutcomeResult(BaseResult):
    """Says how the run ended."""

    outcome: str = Field(description="Who produced the result")


class _ChildParams(BaseParams):
    """Nothing to pass."""


@meta(description="A child run from an error handler", domain=SystemDomain)
@check_roles(GuestRole)
class _ChildAction(BaseAction[_ChildParams, _OutcomeResult]):
    """Answers with its name."""

    @summary_aspect("Answer")
    async def answer_summary(
        self, params: _ChildParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Answer."""
        return _OutcomeResult(outcome="child")


@meta(description="Fails where the params say", domain=SystemDomain)
@check_roles(GuestRole)
class _ReserveAction(BaseAction[_FailParams, _OutcomeResult]):
    """The action from the issue: an aspect writes state, a later step fails, a handler logs it."""

    @regular_aspect("Reserve")
    @result_string("reserved", required=True)
    async def reserve_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Write ``reserved``, unless this is the step that fails."""
        if params.fail_in == "first":
            raise ValueError("planned")
        return {"reserved": "yes"}

    @regular_aspect("Fail")
    @result_string("reserved", required=True)
    async def fail_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Fail where asked, otherwise hand ``reserved`` on: state does not accumulate by itself.

        A ``KeyError`` has no handler.
        """
        if params.fail_in == "second":
            raise ValueError("planned")
        if params.fail_in == "unhandled":
            raise KeyError("planned")
        return {"reserved": state["reserved"]}

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Fail where asked."""
        if params.fail_in == "summary":
            raise ValueError("planned")
        return _OutcomeResult(outcome="summary")

    @on_error(ValueError, description="Planned failure")
    async def reserve_on_error(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _OutcomeResult:
        """Log a field of the handler's state."""
        await box.info(Channel.business, "reserved={%state.reserved}")
        return _OutcomeResult(outcome="handler")


@meta(description="A handler that uses its box for more than logging", domain=OrdersDomain)
@check_roles(GuestRole)
@depends(PaymentServiceResource, factory=lambda: PaymentServiceResource(MagicMock()), description="pay")
class _ToolsHandlerAction(BaseAction[_FailParams, _OutcomeResult]):
    """Its handler runs a child and resolves a dependency."""

    @regular_aspect("Fail")
    async def fail_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Always fail."""
        raise ValueError("planned")

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Never reached."""
        return _OutcomeResult(outcome="summary")

    @on_error(ValueError, description="Use the box")
    async def tools_on_error(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _OutcomeResult:
        """Answer with what the child said and the dependency's type."""
        child = await box.run(_ChildAction, _ChildParams())
        payment = await box.resolve(PaymentServiceResource)
        return _OutcomeResult(outcome=f"{child.outcome}+{type(payment).__name__}")


@meta(description="A handler that asked for context", domain=SystemDomain)
@check_roles(GuestRole)
class _ContextHandlerAction(BaseAction[_FailParams, _OutcomeResult]):
    """Its handler receives a context view and its own state together."""

    @regular_aspect("Reserve")
    @result_string("reserved", required=True)
    async def reserve_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Write ``reserved``."""
        return {"reserved": "yes"}

    @regular_aspect("Fail")
    async def fail_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Always fail."""
        raise ValueError("planned")

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Never reached."""
        return _OutcomeResult(outcome="summary")

    @on_error(ValueError, description="Log with context")
    @context_requires(Ctx.User.user_id)
    async def context_on_error(
        self,
        params: _FailParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        error: ValueError,
        ctx: ContextView,
    ) -> _OutcomeResult:
        """Log state and answer from the view."""
        await box.info(Channel.business, "reserved={%state.reserved}")
        return _OutcomeResult(outcome=str(ctx.get(Ctx.User.user_id)))


class _AnswerParams(BaseParams):
    """Says what the check does."""

    answer: str = Field(default="allow", description="What the check answers")


@meta(description="A check that logs before it answers", domain=SystemDomain)
@check_roles(GuestRole)
class _GatedAction(BaseAction[_AnswerParams, _OutcomeResult]):
    """Its object check answers what the params say."""

    @access_decide("Answer as the params say")
    async def gated_access_decide(self, params: _AnswerParams, box: ToolsBox, connections: Connections) -> Verdict:
        """Log, then answer; a check has no state, so naming a field of it fails."""
        await box.info(Channel.business, "checking")
        if params.answer == "state":
            await box.info(Channel.business, "x={%state.x}")
        if params.answer == "raise":
            raise RuntimeError("planned")
        return FORBIDDEN_OBJECT if params.answer == "refuse" else Allowed()

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _AnswerParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Answer."""
        return _OutcomeResult(outcome="summary")


@meta(description="A check that asked for context", domain=SystemDomain)
@check_roles(GuestRole)
class _ContextCheckAction(BaseAction[_AnswerParams, _OutcomeResult]):
    """Its object check receives a context view and its own box together."""

    @access_decide("Allow the one user")
    @context_requires(Ctx.User.user_id)
    async def context_access_decide(
        self, params: _AnswerParams, box: ToolsBox, connections: Connections, ctx: ContextView
    ) -> Verdict:
        """Log, then answer from the view."""
        await box.info(Channel.business, "checking")
        return Allowed() if ctx.get(Ctx.User.user_id) == "u1" else FORBIDDEN_OBJECT

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _AnswerParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Answer."""
        return _OutcomeResult(outcome="summary")


@meta(description="All five kinds of method, each writing one line", domain=SystemDomain)
@check_roles(GuestRole)
class _AllKindsAction(BaseAction[_FailParams, _OutcomeResult]):
    """One line per kind; a failure in the second step brings in the compensator and the handler."""

    @access_decide("Allow")
    async def all_kinds_access_decide(self, params: _FailParams, box: ToolsBox, connections: Connections) -> Verdict:
        """Write this kind's line."""
        await box.info(Channel.business, "access_decide")
        return Allowed()

    @regular_aspect("Reserve")
    @result_string("reserved", required=True)
    async def reserve_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Write this kind's line."""
        await box.info(Channel.business, "regular")
        return {"reserved": "yes"}

    @compensate(reserve_aspect, "Undo the reservation")
    async def reserve_compensate(
        self,
        params: _FailParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Write this kind's line."""
        await box.info(Channel.business, "compensate")

    @regular_aspect("Fail")
    @result_string("reserved", required=True)
    async def fail_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Fail where asked."""
        if params.fail_in == "second":
            raise ValueError("planned")
        return {"reserved": state["reserved"]}

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Write this kind's line."""
        await box.info(Channel.business, "summary")
        return _OutcomeResult(outcome="summary")

    @on_error(ValueError, description="Planned failure")
    async def all_kinds_on_error(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _OutcomeResult:
        """Write this kind's line."""
        await box.info(Channel.business, "on_error")
        return _OutcomeResult(outcome="handler")


@meta(description="Two handlers, one chosen", domain=SystemDomain)
@check_roles(GuestRole)
class _TwoHandlersAction(BaseAction[_FailParams, _OutcomeResult]):
    """The failure picks the handler."""

    @regular_aspect("Fail")
    async def failing_aspect(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Raise what the params ask for."""
        raise KeyError("planned") if params.fail_in == "key" else ValueError("planned")

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Never reached."""
        return _OutcomeResult(outcome="summary")

    @on_error(ValueError, description="The value handler")
    async def value_on_error(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _OutcomeResult:
        """Write one line."""
        await box.info(Channel.business, "handled")
        return _OutcomeResult(outcome="value")

    @on_error(KeyError, description="The key handler")
    async def key_on_error(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections, error: KeyError
    ) -> _OutcomeResult:
        """Write one line."""
        await box.info(Channel.business, "handled")
        return _OutcomeResult(outcome="key")


@meta(description="Runs a child that fails and handles it", domain=SystemDomain)
@check_roles(GuestRole)
class _ParentAction(BaseAction[_FailParams, _OutcomeResult]):
    """Writes a line, then runs a child whose own handler writes one."""

    @summary_aspect("Run the child")
    async def run_child_summary(
        self, params: _FailParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _OutcomeResult:
        """Write one line and answer with the child."""
        await box.info(Channel.business, "parent")
        return await box.run(_TwoHandlersAction, _FailParams())


@pytest.fixture
def recorder() -> _RecordingLogger:
    """The logger of one test."""
    return _RecordingLogger()


@pytest.fixture
def machine(recorder: _RecordingLogger) -> ActionProductMachine:
    """A machine writing to the recorder."""
    return ActionProductMachine(cache_coordinator=None, log_coordinator=LogCoordinator(loggers=[recorder]))


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_in", ["second", "summary"])
async def test_a_handler_log_reads_the_state_the_handler_received(
    machine: ActionProductMachine, recorder: _RecordingLogger, fail_in: str
) -> None:
    """The line is written with the value, and the handler's result comes back."""
    result = await machine.run(Context(), _ReserveAction(), _FailParams(fail_in=fail_in))

    assert result.outcome == "handler"
    assert [(line.message, line.state) for line in recorder.lines] == [("reserved=yes", {"reserved": "yes"})]


@pytest.mark.asyncio
async def test_a_handler_naming_an_absent_field_still_fails(machine: ActionProductMachine) -> None:
    """Nothing softens templates: nothing was written, so the handler's template fails."""
    with pytest.raises(OnErrorHandlerError, match="reserved"):
        await machine.run(Context(), _ReserveAction(), _FailParams(fail_in="first"))


@pytest.mark.asyncio
async def test_an_error_with_no_handler_goes_up_unchanged(machine: ActionProductMachine) -> None:
    """No handler runs and nothing is written."""
    with pytest.raises(KeyError, match="planned"):
        await machine.run(Context(), _ReserveAction(), _FailParams(fail_in="unhandled"))


@pytest.mark.asyncio
async def test_a_handler_box_still_runs_children_and_resolves_dependencies(machine: ActionProductMachine) -> None:
    """Apart from its name and state, the handler's box does what the shared one did."""
    result = await machine.run(Context(), _ToolsHandlerAction(), _FailParams())

    assert result.outcome == "child+PaymentServiceResource"


@pytest.mark.asyncio
async def test_a_handler_with_context_receives_its_view_and_its_state(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """``@context_requires`` and the handler's own state work together."""
    context = Context(user=UserInfo(user_id="u1"))

    result = await machine.run(context, _ContextHandlerAction(), _FailParams())

    assert result.outcome == "u1"
    assert recorder.lines[0].message == "reserved=yes"


@pytest.mark.asyncio
async def test_a_check_log_has_an_empty_state_on_a_normal_run(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """A check has no state, and its box says so."""
    await machine.run(Context(), _GatedAction(), _AnswerParams())

    assert [line.state for line in recorder.lines] == [{}]


@pytest.mark.asyncio
async def test_a_check_log_has_an_empty_state_when_asked_in_advance(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """Asking in advance gives the check the same box."""
    await machine.check_access_decide(Context(), _GatedAction, _AnswerParams())

    assert [line.state for line in recorder.lines] == [{}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "verdict_type"),
    [("allow", Allowed), ("refuse", Refused), ("raise", Undecided)],
)
async def test_the_check_answers_what_it_answered_before(
    machine: ActionProductMachine, answer: str, verdict_type: type
) -> None:
    """The box changes and the decision does not."""
    assert isinstance(await machine.check_access_decide(Context(), _GatedAction, _AnswerParams(answer=answer)), verdict_type)


@pytest.mark.asyncio
async def test_a_refusal_and_a_failure_leave_a_run_the_way_they_did(machine: ActionProductMachine) -> None:
    """A real call still raises the two exceptions."""
    with pytest.raises(AccessDenied):
        await machine.run(Context(), _GatedAction(), _AnswerParams(answer="refuse"))
    with pytest.raises(AccessUndecided):
        await machine.run(Context(), _GatedAction(), _AnswerParams(answer="raise"))


@pytest.mark.asyncio
async def test_a_check_naming_a_field_of_state_is_undecided_on_both_paths(machine: ActionProductMachine) -> None:
    """It has no state, so the template fails, and a failing check cannot tell."""
    answer = await machine.check_access_decide(Context(), _GatedAction, _AnswerParams(answer="state"))
    assert isinstance(answer, Undecided)
    assert answer.gate is Gate.ACCESS_DECIDE

    with pytest.raises(AccessUndecided) as raised:
        await machine.run(Context(), _GatedAction(), _AnswerParams(answer="state"))
    assert raised.value.verdict.gate is Gate.ACCESS_DECIDE


@pytest.mark.asyncio
async def test_a_check_with_context_receives_its_view_and_its_box(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """``@context_requires`` and the check's own box work together."""
    result = await machine.run(Context(user=UserInfo(user_id="u1")), _ContextCheckAction(), _AnswerParams())

    assert result.outcome == "summary"
    assert [line.message for line in recorder.lines] == ["checking"]


async def _drive(machine: ActionProductMachine, path: str) -> None:
    """Take ``_AllKindsAction`` down one path."""
    if path == "check":
        await machine.check_access_decide(Context(), _AllKindsAction, _FailParams())
    else:
        await machine.run(Context(), _AllKindsAction(), _FailParams(fail_in="second" if path == "failure" else ""))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "kind", "node_type"),
    [
        pytest.param("success", "regular", RegularAspectGraphNode.NODE_TYPE, id="regular_aspect"),
        pytest.param("success", "summary", SummaryAspectGraphNode.NODE_TYPE, id="summary_aspect"),
        pytest.param("failure", "compensate", CompensatorGraphNode.NODE_TYPE, id="compensate"),
        pytest.param("failure", "on_error", ErrorHandlerGraphNode.NODE_TYPE, id="on_error"),
        pytest.param("success", "access_decide", AccessDecideGraphNode.NODE_TYPE, id="access_decide-run"),
        pytest.param("check", "access_decide", AccessDecideGraphNode.NODE_TYPE, id="access_decide-check"),
    ],
)
async def test_the_rule_a_log_line_names_the_node_of_the_method_that_wrote_it(
    machine: ActionProductMachine, recorder: _RecordingLogger, path: str, kind: str, node_type: str
) -> None:
    """The log's action and method names are the id of the method's node, for every kind."""
    await _drive(machine, path)

    line = next(line for line in recorder.lines if line.message == kind)
    assert line.method, f"{kind} wrote its line without a method name"
    assert machine.graph_coordinator.get_node_by_id(f"{line.action}:{line.method}", node_type) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(("fail_in", "handler"), [("value", "value_on_error"), ("key", "key_on_error")])
async def test_the_line_names_the_chosen_handler_not_the_failed_aspect(
    machine: ActionProductMachine, recorder: _RecordingLogger, fail_in: str, handler: str
) -> None:
    """Several handlers: the name is the one that ran."""
    await machine.run(Context(), _TwoHandlersAction(), _FailParams(fail_in=fail_in))

    assert [line.method for line in recorder.lines] == [handler]


@pytest.mark.asyncio
async def test_a_nested_handler_names_itself_at_its_own_level(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """A child's handler keeps the child's action and nesting level."""
    await machine.run(Context(), _ParentAction(), _FailParams())

    parent, child = recorder.lines
    assert child.action.endswith("_TwoHandlersAction")
    assert child.method == "value_on_error"
    assert child.nest_level == parent.nest_level + 1


@pytest.mark.asyncio
async def test_a_compensator_log_reads_the_snapshot_before_its_step(
    machine: ActionProductMachine, recorder: _RecordingLogger
) -> None:
    """Its step wrote ``reserved``; the snapshot was taken before that."""
    await _drive(machine, "failure")

    assert next(line for line in recorder.lines if line.message == "compensate").state == {}
