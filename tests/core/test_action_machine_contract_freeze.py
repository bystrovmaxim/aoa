# tests/core/test_action_machine_contract_freeze.py
"""
Golden contract freeze tests for ActionProductMachine execution flow.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Freeze high-level execution semantics before internal machine decomposition.
These tests verify externally observable behavior that must remain stable
across refactoring steps.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    context + action + params
             │
             ▼
    ActionProductMachine.run/_run_internal
             │
             ├─ role check / connections check
             ├─ regular aspects (0..N)
             ├─ summary aspect (1)
             ├─ optional on_error path
             └─ optional saga rollback path
             │
             ▼
    plugin events + result/exception

Golden checks in this module:
- stage order for successful pipeline;
- error semantics for handled/unhandled failures;
- plugin event sequence around on_error;
- nested run + rollup propagation;
- saga rollback event ordering.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Successful action emits start/regular/summary/finish events in order.
- Handled exceptions return Result; unhandled exceptions propagate.
- Nested child run increments nest level and receives parent rollup flag.
- Saga rollback emits start before per-compensator events and completed last.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `SimpleAction` emits regular+summary sequence and returns greeting result.

Edge case:
- `NoErrorHandlerAction` raises ValueError and no fallback swallows it.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

These tests intentionally assert ordering/contract signals, not internal method
implementations. Event duplication in `TestBench` dual-run mode is avoided by
using direct `ActionProductMachine` execution where strict event order matters.

AI-CORE-BEGIN
ROLE: Golden execution contract test module.
CONTRACT: Lock observable orchestration behavior before decomposition refactor.
INVARIANTS: stage order, error semantics, nested+rollup, saga rollback order.
FLOW: run action -> capture events/result -> assert stable contract.
FAILURES: Any order/semantics drift fails CI before architecture changes merge.
EXTENSION POINTS: Add new contract tests when introducing new orchestrator stages.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.context.context import Context
from action_machine.intents.context.user_info import UserInfo
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.plugins.events import (
    AfterOnErrorAspectEvent,
    BasePluginEvent,
    BeforeOnErrorAspectEvent,
)
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from action_machine.runtime.tools_box import ToolsBox
from action_machine.testing import StubTesterRole, TestBench
from tests.scenarios.domain_model import (
    CompensateAndOnErrorAction,
    CompensateTestParams,
    ErrorHandledAction,
    ErrorTestParams,
    InventoryService,
    NoErrorHandlerAction,
    PaymentService,
    SimpleAction,
)
from tests.scenarios.domain_model.compensate_plugins import SagaObserverPlugin
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole


def _context() -> Context:
    return Context(
        user=UserInfo(
            user_id="contract_tester",
            roles=(AdminRole, ManagerRole, StubTesterRole),
        ),
    )


@dataclass
class _RecordedEvent:
    event_type: str
    nest_level: int


class _EventRecorderPlugin(Plugin):
    """Record ordered stream of emitted plugin events."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[_RecordedEvent] = []

    async def get_initial_state(self) -> dict:
        return {}

    @on(BasePluginEvent)
    async def on_any_event(self, state: dict, event: BasePluginEvent, log) -> dict:
        self.events.append(_RecordedEvent(type(event).__name__, event.nest_level))
        return state


class _OnErrorRecorderPlugin(Plugin):
    """Record only on_error lifecycle events."""

    def __init__(self) -> None:
        super().__init__()
        self.event_types: list[str] = []

    async def get_initial_state(self) -> dict:
        return {}

    @on(BeforeOnErrorAspectEvent)
    async def on_before(self, state: dict, event: BeforeOnErrorAspectEvent, log) -> dict:
        self.event_types.append(type(event).__name__)
        return state

    @on(AfterOnErrorAspectEvent)
    async def on_after(self, state: dict, event: AfterOnErrorAspectEvent, log) -> dict:
        self.event_types.append(type(event).__name__)
        return state


class _NestedParams(BaseParams):
    value: str = "x"


class _NestedResult(BaseResult):
    trace: str


@meta(description="Golden nested child action", domain=TestDomain)
@check_roles(NoneRole)
class _NestedChildAction(BaseAction[_NestedParams, _NestedResult]):
    @summary_aspect("Build child trace")
    async def build_result_summary(
        self,
        params: _NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> _NestedResult:
        return _NestedResult(trace=f"child_nest={box.nested_level};child_rollup={box.rollup}")


@meta(description="Golden nested parent action", domain=TestDomain)
@check_roles(NoneRole)
class _NestedParentAction(BaseAction[_NestedParams, _NestedResult]):
    @regular_aspect("Run nested child")
    @result_string("trace", required=True)
    async def run_child_aspect(
        self,
        params: _NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        child = await box.run(_NestedChildAction, _NestedParams(value=params.value))
        return {
            "trace": (
                f"parent_nest={box.nested_level};parent_rollup={box.rollup};"
                f"{child.trace}"
            ),
        }

    @summary_aspect("Build parent trace")
    async def build_result_summary(
        self,
        params: _NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> _NestedResult:
        return _NestedResult(trace=state["trace"])


def _index_of(events: list[str], event_type: str) -> int:
    return events.index(event_type)


class TestActionMachineContractFreeze:
    """Golden tests for the five execution-contract checkpoints."""

    @pytest.mark.asyncio
    async def test_stage_order_for_successful_pipeline(self) -> None:
        recorder = _EventRecorderPlugin()
        machine = ActionProductMachine(
            mode="test",
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[recorder],
        )

        result = await machine.run(_context(), SimpleAction(), SimpleAction.Params(name="Alice"))
        assert result.greeting == "Hello, Alice!"

        event_types = [e.event_type for e in recorder.events]
        assert _index_of(event_types, "GlobalStartEvent") < _index_of(event_types, "BeforeRegularAspectEvent")
        assert _index_of(event_types, "BeforeRegularAspectEvent") < _index_of(event_types, "AfterRegularAspectEvent")
        assert _index_of(event_types, "AfterRegularAspectEvent") < _index_of(event_types, "BeforeSummaryAspectEvent")
        assert _index_of(event_types, "BeforeSummaryAspectEvent") < _index_of(event_types, "AfterSummaryAspectEvent")
        assert _index_of(event_types, "AfterSummaryAspectEvent") < _index_of(event_types, "GlobalFinishEvent")

    @pytest.mark.asyncio
    async def test_error_semantics_handled_vs_unhandled(self) -> None:
        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
        )

        handled = await bench.run(
            ErrorHandledAction(),
            ErrorTestParams(value="contract", should_fail=True),
            rollup=False,
        )
        assert handled.status == "handled"

        with pytest.raises(ValueError, match="Error: contract_no_handler"):
            await bench.run(
                NoErrorHandlerAction(),
                ErrorTestParams(value="contract_no_handler", should_fail=True),
                rollup=False,
            )

    @pytest.mark.asyncio
    async def test_plugin_sequence_for_on_error_path(self) -> None:
        recorder = _OnErrorRecorderPlugin()
        machine = ActionProductMachine(
            mode="test",
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[recorder],
        )

        result = await machine.run(
            _context(),
            ErrorHandledAction(),
            ErrorTestParams(value="plugin_path", should_fail=True),
        )
        assert result.status == "handled"
        assert recorder.event_types == [
            "BeforeOnErrorAspectEvent",
            "AfterOnErrorAspectEvent",
        ]

    @pytest.mark.asyncio
    async def test_nested_run_and_rollup_propagation(self) -> None:
        machine = ActionProductMachine(
            mode="test",
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
        )

        result = await machine._run_internal(
            context=_context(),
            action=_NestedParentAction(),
            params=_NestedParams(value="x"),
            resources=None,
            connections=None,
            nested_level=0,
            rollup=True,
        )

        assert "parent_nest=1" in result.trace
        assert "parent_rollup=True" in result.trace
        assert "child_nest=2" in result.trace
        assert "child_rollup=True" in result.trace

    @pytest.mark.asyncio
    async def test_saga_rollback_event_order(self, mock_payment, mock_inventory) -> None:
        observer = SagaObserverPlugin()
        observer.reset()

        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            plugins=[observer],
        )

        result = await bench.run(
            CompensateAndOnErrorAction(),
            CompensateTestParams(
                user_id="golden_user",
                amount=100.0,
                item_id="ITEM-GOLDEN-1",
                should_fail=True,
            ),
            rollup=False,
        )
        assert result.status == "handled_after_compensate"

        # TestBench runs async and sync machines; validate the last rollback segment.
        events: list[dict[str, Any]] = observer.collected_events
        start_idx = max(i for i, e in enumerate(events) if e["event_type"] == "SagaRollbackStartedEvent")
        segment = events[start_idx:]
        types = [e["event_type"] for e in segment]

        assert types[0] == "SagaRollbackStartedEvent"
        assert types[-1] == "SagaRollbackCompletedEvent"
        assert "BeforeCompensateAspectEvent" in types
        assert any(t in types for t in ("AfterCompensateAspectEvent", "CompensateFailedEvent"))

