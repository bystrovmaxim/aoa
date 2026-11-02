# packages/aoa-action-machine/tests/action_machine/runtime/test_emission_rules.py
"""
What a method may write — the typed zones, and the lines that stay as they were.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each of the five kinds of method is run with ``@emits`` and without it. A refusal reaches
no logger and takes the ordinary path of the method that made it. With no switch on,
lines with ``kwargs`` and with no variables stay what they were: that form is kept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions import AccessUndecided
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from aoa.action_machine.intents.access_control import Allowed, Undecided, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on import on
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.plugin.core.events import GlobalFinishEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.sync_action_product_machine import SyncActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.testing.bench import TestBench

from ...support.domain_model.domains import SystemDomain

KINDS = ("access", "regular", "compensate", "handler", "summary")


class ListedEvent(BaseEvent):
    """The fact every typed method lists."""

    order_id: str


class AlsoListedEvent(BaseEvent):
    """A second listed fact."""


class UnlistedEvent(BaseEvent):
    """A fact no method lists."""


@dataclass(frozen=True)
class _Line:
    """One written line."""

    method: str
    message: str
    var: Any


class _RecordingLogger(BaseLogger):
    """A logger keeping every line."""

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
        self.lines.append(_Line(getattr(scope, "aspect", ""), message, var))

    def messages(self) -> list[str]:
        """Return the text of every line."""
        return [line.message for line in self.lines]


class _Params(BaseParams):
    """Says which method speaks, what it writes, and whether the run fails."""

    speaker: str = Field(default="", description="The kind of method that writes")
    write: str = Field(default="", description="What it writes")
    fail: bool = Field(default=False, description="Whether a later step fails")


class _Result(BaseResult):
    """Says who answered."""

    outcome: str = Field(description="Who produced the result")


async def _say(box: ToolsBox, params: _Params, kind: str) -> None:
    """Write what the params ask for, when this kind is the speaker; a helper shares the method's box."""
    if params.speaker != kind:
        return
    if params.write == "listed":
        await box.info(Channel.business, "listed {%var.order_id}", ListedEvent(order_id="o1"))
    elif params.write == "unlisted":
        await box.info(Channel.business, "unlisted", UnlistedEvent())
    elif params.write == "kwargs":
        await box.info(Channel.business, "kwargs {%var.x}", x=1)
    elif params.write == "plain":
        await box.info(Channel.business, "plain")
    elif params.write == "broken":
        await box.info(Channel.business, "{%var.absent}", UnlistedEvent())


@meta(description="All five kinds of method, each a typed zone", domain=SystemDomain)
@check_roles(GuestRole)
class _TypedAction(BaseAction[_Params, _Result]):
    """Every method declares ``ListedEvent``; the last compensator always reports."""

    @access_decide("Allow")
    @emits(ListedEvent)
    async def typed_access_decide(self, params: _Params, box: ToolsBox, connections: Connections) -> Verdict:
        """Speak, then allow."""
        await _say(box, params, "access")
        return Allowed()

    @regular_aspect("First")
    @emits(ListedEvent)
    async def first_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Speak."""
        await _say(box, params, "regular")
        return {}

    @compensate(first_aspect, "Undo the first step")
    @emits(ListedEvent)
    async def first_compensate(
        self,
        params: _Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Report that the rollback reached this step."""
        await box.info(Channel.business, "first undone", ListedEvent(order_id="o1"))

    @regular_aspect("Second")
    async def second_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Do nothing."""
        return {}

    @compensate(second_aspect, "Undo the second step")
    @emits(ListedEvent)
    async def second_compensate(
        self,
        params: _Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Speak."""
        await _say(box, params, "compensate")

    @regular_aspect("Third")
    async def third_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Fail when asked."""
        if params.fail:
            raise ValueError("planned")
        return {}

    @summary_aspect("Finish")
    @emits(ListedEvent, AlsoListedEvent)
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Speak."""
        await _say(box, params, "summary")
        return _Result(outcome="summary")

    @on_error(ValueError, description="Answer for the planned failure")
    @emits(ListedEvent)
    async def planned_on_error(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _Result:
        """Speak."""
        await _say(box, params, "handler")
        return _Result(outcome="handler")


@meta(description="All five kinds of method, no switch on", domain=SystemDomain)
@check_roles(GuestRole)
class _PlainAction(BaseAction[_Params, _Result]):
    """The same shape as ``_TypedAction``, with no ``@emits``."""

    @access_decide("Allow")
    async def plain_access_decide(self, params: _Params, box: ToolsBox, connections: Connections) -> Verdict:
        """Speak, then allow."""
        await _say(box, params, "access")
        return Allowed()

    @regular_aspect("First")
    async def first_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Speak."""
        await _say(box, params, "regular")
        return {}

    @compensate(first_aspect, "Undo the first step")
    async def first_compensate(
        self,
        params: _Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Speak."""
        await _say(box, params, "compensate")

    @regular_aspect("Second")
    async def second_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Fail when asked."""
        if params.fail:
            raise ValueError("planned")
        return {}

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Speak."""
        await _say(box, params, "summary")
        return _Result(outcome="summary")

    @on_error(ValueError, description="Answer for the planned failure")
    async def planned_on_error(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> _Result:
        """Speak."""
        await _say(box, params, "handler")
        return _Result(outcome="handler")


@meta(description="A handler that takes every exception", domain=SystemDomain)
@check_roles(GuestRole)
class _CatchAllAction(BaseAction[_Params, _Result]):
    """A refusal in its aspect is an exception like any other."""

    @regular_aspect("Speak")
    @emits(ListedEvent)
    async def speak_aspect(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        """Speak."""
        await _say(box, params, "regular")
        return {}

    @summary_aspect("Finish")
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Answer."""
        return _Result(outcome="summary")

    @on_error(Exception, description="Take everything")
    async def everything_on_error(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> _Result:
        """Answer with the type of the error."""
        return _Result(outcome=type(error).__name__)


@meta(description="A result that comes from the cache", domain=SystemDomain)
@check_roles(GuestRole)
class _CachedAction(BaseAction[_Params, _Result]):
    """Its summary emits only when it runs."""

    def cache_key(self, params: _Params) -> str | None:
        """Every call shares one entry."""
        return "fixed"

    async def on_cache_write(self, result: _Result, params: _Params, duration_ms: float) -> list[CacheTag] | None:
        """Keep the result."""
        return [CacheTag(key="fixed")]

    async def read_cache(self, params: _Params, entry: CacheEntry) -> _Result | None:
        """Serve the kept result."""
        return _Result(outcome="cache")

    @summary_aspect("Finish")
    @emits(ListedEvent)
    async def finish_summary(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> _Result:
        """Emit, then answer."""
        await box.info(Channel.business, "ran", ListedEvent(order_id="o1"))
        return _Result(outcome="summary")


class _WritingPlugin(Plugin):
    """A plugin writing a line with no event at the end of every run."""

    async def get_initial_state(self) -> dict[str, Any]:
        """Keep nothing."""
        return {}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_finish(self, state: dict[str, Any], event: GlobalFinishEvent, log: Any) -> dict[str, Any]:
        """Write one plain line."""
        await log.info(Channel.debug, "plugin line {%var.x}", x=1)
        return state


def _machine(logger: BaseLogger, **kwargs: Any) -> ActionProductMachine:
    """Build a machine that writes to ``logger``."""
    return ActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]), **kwargs)


def _params(speaker: str, write: str) -> _Params:
    """Ask ``speaker`` to write ``write``; the two kinds that run on failure need the failure."""
    return _Params(speaker=speaker, write=write, fail=speaker in ("compensate", "handler"))


# ── A method with @emits ─────────────────────────────────────────────────────


@pytest.mark.parametrize("kind", KINDS)
async def test_a_listed_event_is_delivered(kind: str) -> None:
    logger = _RecordingLogger()

    await _machine(logger).run(Context(), _TypedAction(), _params(kind, "listed"))

    assert "listed o1" in logger.messages()
    delivered = next(line for line in logger.lines if line.message == "listed o1")
    assert isinstance(delivered.var, ListedEvent)


async def test_either_listed_event_or_neither_may_be_written() -> None:
    assert (await _machine(_RecordingLogger()).run(Context(), _TypedAction(), _Params())).outcome == "summary"


@pytest.mark.parametrize("write", ["unlisted", "kwargs", "plain"])
async def test_a_refused_aspect_fails_and_reaches_no_logger(write: str) -> None:
    logger = _RecordingLogger()

    with pytest.raises(EventContractError, match=r"_TypedAction\.first_aspect"):
        await _machine(logger).run(Context(), _TypedAction(), _Params(speaker="regular", write=write))

    assert "first undone" in logger.messages()
    assert not {"unlisted", "kwargs 1", "plain"} & set(logger.messages())


@pytest.mark.parametrize("write", ["unlisted", "kwargs", "plain"])
async def test_a_refused_summary_fails_and_reaches_no_logger(write: str) -> None:
    logger = _RecordingLogger()

    with pytest.raises(EventContractError, match=r"_TypedAction\.finish_summary"):
        await _machine(logger).run(Context(), _TypedAction(), _Params(speaker="summary", write=write))

    assert not {"unlisted", "kwargs 1", "plain"} & set(logger.messages())


async def test_a_refusal_names_what_was_refused() -> None:
    with pytest.raises(EventContractError, match="UnlistedEvent"):
        await _machine(_RecordingLogger()).run(Context(), _TypedAction(), _Params(speaker="regular", write="unlisted"))


async def test_a_broad_handler_catches_a_refusal_and_nothing_was_delivered() -> None:
    logger = _RecordingLogger()

    result = await _machine(logger).run(Context(), _CatchAllAction(), _Params(speaker="regular", write="unlisted"))

    assert result.outcome == "EventContractError"
    assert not logger.lines


@pytest.mark.parametrize("write", ["unlisted", "kwargs", "plain"])
async def test_a_refused_compensator_counts_as_failed_and_the_rollback_goes_on(write: str) -> None:
    logger = _RecordingLogger()

    result = await _machine(logger).run(Context(), _TypedAction(), _params("compensate", write))

    assert result.outcome == "handler"
    assert logger.messages() == ["first undone"]


@pytest.mark.parametrize("write", ["unlisted", "kwargs", "plain"])
async def test_a_refused_handler_gives_the_handler_error(write: str) -> None:
    logger = _RecordingLogger()

    with pytest.raises(OnErrorHandlerError, match="may not write"):
        await _machine(logger).run(Context(), _TypedAction(), _params("handler", write))


@pytest.mark.parametrize("write", ["unlisted", "kwargs", "plain"])
async def test_a_refused_access_decision_is_undecided_on_both_paths(write: str) -> None:
    logger = _RecordingLogger()
    machine = _machine(logger)
    params = _Params(speaker="access", write=write)

    assert isinstance(await machine.check_access_decide(Context(), _TypedAction, params), Undecided)
    with pytest.raises(AccessUndecided):
        await machine.run(Context(), _TypedAction(), params)
    assert not logger.lines


async def test_an_access_decision_delivers_on_both_paths() -> None:
    logger = _RecordingLogger()
    machine = _machine(logger)
    params = _Params(speaker="access", write="listed")

    await machine.check_access_decide(Context(), _TypedAction, params)
    assert logger.messages() == ["listed o1"]

    await machine.run(Context(), _TypedAction(), params)
    assert logger.messages() == ["listed o1", "listed o1"]


async def test_a_refusal_comes_before_a_broken_template() -> None:
    with pytest.raises(EventContractError):
        await _machine(_RecordingLogger()).run(Context(), _TypedAction(), _Params(speaker="regular", write="broken"))


async def test_another_method_of_the_action_keeps_its_kwargs() -> None:
    @meta(description="One typed method beside a plain one", domain=SystemDomain)
    @check_roles(GuestRole)
    class MixedAction(BaseAction[_Params, _Result]):
        """The aspect keeps ``kwargs``; the summary is typed."""

        @regular_aspect("Plain")
        async def plain_aspect(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> dict[str, Any]:
            """Write a plain line."""
            await box.info(Channel.business, "kept {%var.x}", x=1)
            return {}

        @summary_aspect("Typed")
        @emits(ListedEvent)
        async def typed_summary(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> _Result:
            """Answer."""
            return _Result(outcome="summary")

    logger = _RecordingLogger()

    await _machine(logger).run(Context(), MixedAction(), _Params())

    assert logger.messages() == ["kept 1"]


async def test_a_plugin_line_goes_out_around_a_typed_method() -> None:
    logger = _RecordingLogger()

    await _machine(logger, plugins=[_WritingPlugin()]).run(
        Context(), _TypedAction(), _Params(speaker="summary", write="listed")
    )

    assert logger.messages() == ["listed o1", "plugin line 1"]


async def test_the_machines_own_line_goes_out_around_a_typed_method(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _RecordingLogger()
    machine = _machine(logger)

    async def failing_rollback(**kwargs: Any) -> None:
        raise RuntimeError("rollback broke")

    monkeypatch.setattr(machine._saga_coordinator, "execute", failing_rollback)  # pylint: disable=protected-access

    await machine.run(Context(), _TypedAction(), _Params(fail=True))

    assert len(logger.lines) == 1
    assert "rollback" in logger.lines[0].message.lower()


async def test_a_result_from_the_cache_delivers_nothing() -> None:
    logger = _RecordingLogger()
    machine = _machine(logger, cache_coordinator=CacheCoordinator())

    first = await machine.run(Context(), _CachedAction(), _Params())
    second = await machine.run(Context(), _CachedAction(), _Params())

    assert (first.outcome, second.outcome) == ("summary", "cache")
    assert logger.messages() == ["ran"]


def test_the_rules_hold_on_the_sync_machine() -> None:
    logger = _RecordingLogger()
    machine = SyncActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]))

    machine.run(Context(), _TypedAction(), _Params(speaker="summary", write="listed"))
    with pytest.raises(EventContractError):
        machine.run(Context(), _TypedAction(), _Params(speaker="summary", write="kwargs"))

    assert "listed o1" in logger.messages()
    assert "kwargs 1" not in logger.messages()


# ── TestBench ────────────────────────────────────────────────────────────────


def _bench(logger: BaseLogger) -> TestBench:
    """Build a bench that writes to ``logger``."""
    return TestBench(log_coordinator=LogCoordinator(loggers=[logger]))


async def _bench_run(bench: TestBench, action: BaseAction[Any, Any], entry: str, params: _Params) -> None:
    """Run one method directly."""
    if entry == "aspect":
        await bench.run_aspect(action, "first_aspect", params, state={}, rollup=False)
    elif entry == "summary":
        await bench.run_summary(action, params, state={}, rollup=False)
    else:
        await bench.run_compensator(
            action,
            "first_compensate",
            params=params,
            state_before=BaseState(),
            state_after=None,
            error=ValueError("planned"),
        )


@pytest.mark.parametrize(("entry", "kind"), [("aspect", "regular"), ("summary", "summary")])
async def test_a_direct_run_raises_what_a_normal_run_raises(entry: str, kind: str) -> None:
    logger = _RecordingLogger()
    params = _Params(speaker=kind, write="unlisted")

    with pytest.raises(EventContractError) as direct:
        await _bench_run(_bench(logger), _TypedAction(), entry, params)
    with pytest.raises(EventContractError) as normal:
        await _machine(_RecordingLogger()).run(Context(), _TypedAction(), params)

    assert str(direct.value) == str(normal.value)
    assert not logger.lines


async def test_a_direct_run_of_a_compensator_is_refused() -> None:
    @meta(description="A compensator that writes a plain line", domain=SystemDomain)
    @check_roles(GuestRole)
    class CompensatorAction(BaseAction[_Params, _Result]):
        """Its compensator breaks its own declaration."""

        @regular_aspect("First")
        async def first_aspect(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> dict[str, Any]:
            """Do nothing."""
            return {}

        @compensate(first_aspect, "Undo")
        @emits(ListedEvent)
        async def first_compensate(
            self,
            params: _Params,
            state_before: BaseState,
            state_after: BaseState | None,
            box: ToolsBox,
            connections: Connections,
            error: Exception,
        ) -> None:
            """Write a line with no event."""
            await box.info(Channel.business, "plain")

        @summary_aspect("Finish")
        async def finish_summary(
            self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> _Result:
            """Answer."""
            return _Result(outcome="summary")

    logger = _RecordingLogger()

    with pytest.raises(EventContractError, match="first_compensate"):
        await _bench_run(_bench(logger), CompensatorAction(), "compensator", _Params())

    assert not logger.lines


# ── The form that stays: lines with kwargs and with no variables ─────────────


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(("write", "message"), [("kwargs", "kwargs 1"), ("plain", "plain")])
async def test_with_no_switch_on_each_kind_writes_as_before(kind: str, write: str, message: str) -> None:
    logger = _RecordingLogger()

    await _machine(logger).run(Context(), _PlainAction(), _params(kind, write))

    assert logger.messages() == [message]
    assert type(logger.lines[0].var) is dict


@pytest.mark.parametrize("kind", KINDS)
async def test_with_no_switch_on_a_method_may_still_emit_an_event(kind: str) -> None:
    logger = _RecordingLogger()

    await _machine(logger).run(Context(), _PlainAction(), _params(kind, "unlisted"))

    assert isinstance(logger.lines[0].var, UnlistedEvent)


def test_with_no_switch_on_the_sync_machine_writes_as_before() -> None:
    logger = _RecordingLogger()
    machine = SyncActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]))

    machine.run(Context(), _PlainAction(), _Params(speaker="summary", write="kwargs"))

    assert logger.messages() == ["kwargs 1"]
    assert type(logger.lines[0].var) is dict


@pytest.mark.parametrize(("entry", "kind"), [("aspect", "regular"), ("summary", "summary"), ("compensator", "compensate")])
@pytest.mark.parametrize(("write", "message"), [("kwargs", "kwargs 1"), ("plain", "plain")])
async def test_with_no_switch_on_a_direct_run_writes_as_before(entry: str, kind: str, write: str, message: str) -> None:
    logger = _RecordingLogger()

    await _bench_run(_bench(logger), _PlainAction(), entry, _Params(speaker=kind, write=write))

    assert logger.messages() == [message]
    assert type(logger.lines[0].var) is dict
