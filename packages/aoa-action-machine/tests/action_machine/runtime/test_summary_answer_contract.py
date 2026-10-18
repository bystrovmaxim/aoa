# packages/aoa-action-machine/tests/action_machine/runtime/test_summary_answer_contract.py
"""
Tests for a summary's answer — the operation's Result, at both moments.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@summary_aspect`` assembles the operation's answer. The documentation has always said
it "must return a typed ``Result``"; until this feature nothing compared the two, so an
operation declaring ``ResultStub`` could answer with a ``dict`` and no layer objected
(measured on the tree before the change: ``answer type: dict``, ``is ResultStub:
False``).

Two moments make the sentence true. At assembly the declared return is compared with the
operation's ``Result``. At run time the returned value is compared with the same
``Result`` — the only way to catch a method that contradicts its own annotation.

The last class keeps the change honest: a compliant operation answers what it answered
before, publishes the same events, and writes the same log messages.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheAnnotationAtAssembly — Any and a foreign Result refused; the base and its own accepted
TestTheAnswerAtRuntime      — a mapping, a foreign Result, and the operation's own Result
TestNothingElseMoved        — the compliant operation: same answer, same events, same log
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions import ActionResultTypeError, AspectSignatureError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on.on_decorator import on
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub
from aoa.action_machine.plugin.core.events import BasePluginEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain

_SEEN_EVENTS: list[str] = []
"""Event names the recorder saw during the run, in order."""


class OtherResult(BaseResult):
    """A result that belongs to some other operation."""


class _EventRecorder(Plugin):
    """A plugin recording the name of every event the run publishes."""

    async def get_initial_state(self) -> dict[str, Any]:
        """Nothing to keep between events."""
        return {}

    @on(BasePluginEvent, ignore_exceptions=False)
    async def on_any(self, state: dict[str, Any], event: BasePluginEvent, log: Any) -> dict[str, Any]:
        """Record one event name."""
        _SEEN_EVENTS.append(type(event).__name__)
        return state


class _RecordingLogger(BaseLogger):
    """A logger collecting the messages the run writes."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

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
        """Append one written message."""
        self.messages.append(message)


@meta(description="answer: a compliant summary", domain=SystemDomain)
@check_roles(GuestRole)
class CompliantAnswerAction(BaseAction[ParamsStub, ResultStub]):
    """An operation whose summary answers with its own Result."""

    @summary_aspect("Assemble the result")
    async def good_answer_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ResultStub:
        """Build the empty result."""
        return ResultStub()


def _context() -> Context:
    """A caller the operation admits."""
    return Context()


def _machine(logger: BaseLogger | None = None) -> ActionProductMachine:
    """A machine with the recorder plugin, and optionally a recording logger."""
    return ActionProductMachine(
        cache_coordinator=None,
        plugins=[_EventRecorder()],
        log_coordinator=LogCoordinator(loggers=[logger] if logger is not None else []),
    )


class TestTheAnnotationAtAssembly:
    """The declared return is the operation's Result — where the operation's names exist."""

    def test_a_summary_annotated_any_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="a summary answers with the operation's Result"):

            @exclude_graph_model
            @meta(description="answer: a summary that promises anything", domain=SystemDomain)
            @check_roles(GuestRole)
            class AnyAnswerAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def any_answer_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                ) -> Any:
                    return ResultStub()

            ActionGraphNode(AnyAnswerAction)

    def test_a_summary_naming_a_foreign_result_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="OtherResult"):

            @exclude_graph_model
            @meta(description="answer: a summary naming a foreign result", domain=SystemDomain)
            @check_roles(GuestRole)
            class ForeignAnswerAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def foreign_answer_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                ) -> OtherResult:
                    return OtherResult()

            ActionGraphNode(ForeignAnswerAction)

    def test_the_operations_own_result_is_accepted(self) -> None:
        assert ActionGraphNode(CompliantAnswerAction).get_summary_aspect_graph_node().label == "good_answer_summary"

    def test_the_base_result_is_accepted(self) -> None:
        @meta(description="answer: a summary naming the base result", domain=SystemDomain)
        @check_roles(GuestRole)
        class BaseAnswerAction(BaseAction[ParamsStub, ResultStub]):
            @summary_aspect("S")
            async def base_answer_summary(
                self,
                params: ParamsStub,
                state: BaseState,
                box: ToolsBox,
                connections: dict[str, BaseResource],
            ) -> BaseResult:
                return ResultStub()

        assert ActionGraphNode(BaseAnswerAction).get_summary_aspect_graph_node().label == "base_answer_summary"


class TestTheAnswerAtRuntime:
    """The returned value is compared with the same Result, after the method returns."""

    def test_a_mapping_is_refused(self) -> None:
        @meta(description="answer: a summary returning a mapping", domain=SystemDomain)
        @check_roles(GuestRole)
        class MappingAnswerAction(BaseAction[ParamsStub, ResultStub]):
            @summary_aspect("S")
            async def mapping_answer_summary(
                self,
                params: ParamsStub,
                state: BaseState,
                box: ToolsBox,
                connections: dict[str, BaseResource],
            ) -> ResultStub:
                return {"not": "a result"}  # type: ignore[return-value]

        with pytest.raises(ActionResultTypeError) as caught:
            asyncio.run(_machine().run(_context(), MappingAnswerAction(), ParamsStub()))

        message = str(caught.value)
        assert "MappingAnswerAction" in message
        assert "ResultStub" in message
        assert "dict" in message

    def test_a_foreign_result_is_refused(self) -> None:
        @meta(description="answer: a summary returning a foreign result", domain=SystemDomain)
        @check_roles(GuestRole)
        class ForeignInstanceAction(BaseAction[ParamsStub, ResultStub]):
            @summary_aspect("S")
            async def foreign_instance_summary(
                self,
                params: ParamsStub,
                state: BaseState,
                box: ToolsBox,
                connections: dict[str, BaseResource],
            ) -> ResultStub:
                return OtherResult()  # type: ignore[return-value]

        with pytest.raises(ActionResultTypeError, match="OtherResult"):
            asyncio.run(_machine().run(_context(), ForeignInstanceAction(), ParamsStub()))

    def test_the_operations_own_result_is_handed_back(self) -> None:
        answer = asyncio.run(_machine().run(_context(), CompliantAnswerAction(), ParamsStub()))

        assert isinstance(answer, ResultStub)


class TestNothingElseMoved:
    """A compliant operation answers what it answered before, with the same events and log."""

    def test_the_answer_is_unchanged(self) -> None:
        _SEEN_EVENTS.clear()
        answer = asyncio.run(_machine().run(_context(), CompliantAnswerAction(), ParamsStub()))

        assert type(answer) is ResultStub

    def test_the_event_sequence_is_unchanged(self) -> None:
        _SEEN_EVENTS.clear()
        asyncio.run(_machine().run(_context(), CompliantAnswerAction(), ParamsStub()))

        assert _SEEN_EVENTS == [
            "GlobalStartEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    def test_the_log_written_is_unchanged(self) -> None:
        logger = _RecordingLogger()
        asyncio.run(_machine(logger).run(_context(), CompliantAnswerAction(), ParamsStub()))

        assert logger.messages == []

    def test_the_run_refuses_nothing_for_a_compliant_answer(self) -> None:
        _SEEN_EVENTS.clear()
        asyncio.run(_machine().run(_context(), CompliantAnswerAction(), ParamsStub()))

        assert "OnErrorAspectEvent" not in _SEEN_EVENTS
