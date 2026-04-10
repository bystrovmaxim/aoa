"""
Constructor extension points for ActionProductMachine.

Verifies custom strategy injection via keyword-only constructor parameters for:
- role checker
- connection validator
- aspect executor
- error handler executor
- saga coordinator
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.compensate.compensate_decorator import compensate
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.saga_frame import SagaFrame
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from tests.domain_model import PingAction


@pytest.fixture()
def context() -> Context:
    return Context(user=UserInfo(user_id="u1", roles=[]))


@dataclass(frozen=True)
class _HandledResult(BaseResult):
    marker: str


@meta(description="Action with regular + failing summary for saga override tests")
@check_roles(ROLE_NONE)
class _FailingSagaAction(BaseAction[BaseParams, BaseResult]):
    @regular_aspect("touch")
    async def touch_aspect(self, params, state, box, connections):
        return {}

    @compensate("touch_aspect", "rollback touch")
    async def rollback_touch_compensate(
        self,
        params,
        state_before,
        state_after,
        box,
        connections,
        error,
    ) -> None:
        _ = (params, state_before, state_after, box, connections, error)

    @summary_aspect("boom")
    async def build_summary(self, params, state, box, connections):
        raise ValueError("boom")


class _RoleCheckerFake:
    def __init__(self) -> None:
        self.called = False

    def check(self, action, context, runtime) -> None:
        _ = (action, context, runtime)
        self.called = True


class _ConnectionValidatorFake:
    def __init__(self) -> None:
        self.called = False

    def validate(self, action, connections, runtime):
        _ = (action, runtime)
        self.called = True
        return connections or {}


class _AspectExecutorFake:
    def __init__(self) -> None:
        self.regular_called = 0
        self.summary_called = 0

    async def call(self, machine: object, **kwargs: Any):
        _ = (machine, kwargs)
        return {}

    async def execute_regular(
        self,
        machine: object,
        *,
        aspect_meta,
        action,
        params,
        state,
        box,
        connections,
        context,
        runtime,
        saga_stack: list[SagaFrame],
    ) -> tuple[BaseState, dict[str, Any], float]:
        _ = (
            machine,
            aspect_meta,
            action,
            params,
            box,
            connections,
            context,
            runtime,
            saga_stack,
        )
        self.regular_called += 1
        return state, {}, 0.0

    async def execute_summary(
        self,
        machine: object,
        *,
        summary_meta,
        action,
        params,
        state,
        box,
        connections,
        context,
    ) -> tuple[BaseResult, float]:
        _ = (machine, summary_meta, action, params, state, box, connections, context)
        self.summary_called += 1
        return PingAction.Result(message="fake"), 0.0


class _ErrorHandlerFake:
    def __init__(self) -> None:
        self.called = False

    async def handle(self, machine: object, **kwargs: Any) -> BaseResult:
        _ = (machine, kwargs)
        self.called = True
        return _HandledResult(marker="handled")


class _SagaCoordinatorFake:
    def __init__(self) -> None:
        self.called = False
        self.frames = 0

    async def execute(
        self,
        machine: object,
        *,
        saga_stack: list[SagaFrame],
        error: Exception,
        action: BaseAction[Any, Any],
        params: BaseParams,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        plugin_ctx,
    ) -> None:
        _ = (machine, error, action, params, box, connections, context, plugin_ctx)
        self.called = True
        self.frames = len(saga_stack)


@pytest.mark.asyncio
async def test_custom_role_and_connection_strategies_are_used(context: Context) -> None:
    role_checker = _RoleCheckerFake()
    connection_validator = _ConnectionValidatorFake()
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
        role_checker=role_checker,  # type: ignore[arg-type]
        connection_validator=connection_validator,  # type: ignore[arg-type]
    )

    result = await machine.run(context, PingAction(), PingAction.Params())

    assert result.message == "pong"
    assert role_checker.called is True
    assert connection_validator.called is True


@pytest.mark.asyncio
async def test_custom_aspect_executor_is_used_for_summary(context: Context) -> None:
    aspect_executor = _AspectExecutorFake()
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
        aspect_executor=aspect_executor,  # type: ignore[arg-type]
    )

    result = await machine.run(context, PingAction(), PingAction.Params())

    assert result.message == "fake"
    assert aspect_executor.summary_called == 1


@pytest.mark.asyncio
async def test_custom_error_handler_and_saga_are_used(context: Context) -> None:
    error_handler = _ErrorHandlerFake()
    saga = _SagaCoordinatorFake()
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
        error_handler_executor=error_handler,  # type: ignore[arg-type]
        saga_coordinator=saga,  # type: ignore[arg-type]
    )

    result = await machine.run(context, _FailingSagaAction(), BaseParams())

    assert isinstance(result, _HandledResult)
    assert result.marker == "handled"
    assert error_handler.called is True
    assert saga.called is True
    assert saga.frames >= 1
