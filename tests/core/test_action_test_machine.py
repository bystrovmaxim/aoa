# tests/core/test_action_test_machine.py
"""
Tests for ActionTestMachine — test action machine with mock support.

Checks:
- Running MockAction directly (without aspects)
- Running real actions with mocked dependencies
- Mock preparation (_prepare_mock)
- build_factory method
- Passing mode and log_coordinator (constructor changes)
- Default mode="test"

Изменения (этап 1):
- Во всех аспектах заменены сигнатуры: параметры deps и log заменены на box: ToolsBox.
- Обновлены вызовы box.resolve(...) вместо deps.get(...).
- Обновлены вызовы box.info(...) вместо log.info(...).
- Убраны неиспользуемые импорты ActionBoundLogger где необходимо.

Изменения (этап 2):
- Исправлены асинхронные тесты: добавлены async def и декоратор @pytest.mark.anyio
  для методов, использующих await.

Изменения (этап 3 — миграция на шлюзы):
- Все тестовые действия теперь наследуют BaseAction напрямую (не MockAction)
  и определяют собственный @summary_aspect.
- Все тестовые действия декорированы @CheckRoles(CheckRoles.NONE, desc="").
"""

from unittest.mock import AsyncMock, Mock

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.ActionTestMachine import ActionTestMachine
from action_machine.dependencies.depends import depends
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.Core.MockAction import MockAction
from action_machine.Core.ToolsBox import ToolsBox
from action_machine.Logging.log_coordinator import LogCoordinator


# ----------------------------------------------------------------------
# Helper classes
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class RealAction(BaseAction[MockParams, MockResult]):
    """Real action with a str dependency."""
    captured = None
    log_called = False

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        self.captured = box.resolve(str)
        # Check that the logger works
        await box.info("Summary executed", action="RealAction")
        self.log_called = True
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
@depends(int)
class ActionWithDeps(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class CapturingAction(BaseAction[MockParams, MockResult]):
    """Action that captures the obtained dependency and calls the logger."""
    captured = None
    log_messages = []

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        self.captured = box.resolve(str)
        await box.debug("Debug from CapturingAction")
        await box.info("Info from CapturingAction")
        return MockResult()


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def machine(empty_context: Context) -> ActionTestMachine:
    """Test machine with default mode (test) and mock log coordinator."""
    mock_log_coordinator = AsyncMock(spec=LogCoordinator)
    return ActionTestMachine(
        mode="test",
        log_coordinator=mock_log_coordinator,
    )


@pytest.fixture
def machine_with_mocks() -> ActionTestMachine:
    """Machine with pre‑configured mocks."""
    mocks = {
        str: "mocked_string",
        int: MockAction(result=MockResult()),
        list: lambda p: ["called"],
    }
    return ActionTestMachine(mocks=mocks, mode="testing_mode")


# ======================================================================
# TESTS: Constructor
# ======================================================================
class TestConstructor:
    def test_default_mode_is_test(self, empty_context: Context) -> None:
        """Default mode is 'test'."""
        machine = ActionTestMachine()
        assert machine._mode == "test"

    def test_custom_mode_passed_to_parent(self, empty_context: Context) -> None:
        """Custom mode is passed to the parent class."""
        machine = ActionTestMachine(mode="custom_mode")
        assert machine._mode == "custom_mode"

    def test_log_coordinator_passed_to_parent(self, empty_context: Context) -> None:
        """Provided log_coordinator is used in the parent."""
        mock_coord = AsyncMock(spec=LogCoordinator)
        machine = ActionTestMachine(log_coordinator=mock_coord)
        assert machine._log_coordinator is mock_coord


# ======================================================================
# TESTS: run() with MockAction
# ======================================================================
class TestRunWithMockAction:
    @pytest.mark.anyio
    async def test_run_mock_action_directly(self, machine: ActionTestMachine, empty_context: Context) -> None:
        """MockAction runs directly, bypassing aspects."""
        mock_action = MockAction(result=MockResult())
        params = MockParams()
        original_run = mock_action.run
        mock_action.run = Mock(wraps=original_run)

        result = await machine.run(empty_context, mock_action, params)

        mock_action.run.assert_called_once_with(params)
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_mock_action_tracks_calls(self, machine: ActionTestMachine, empty_context: Context) -> None:
        """MockAction counts calls and stores last parameters."""
        mock_action = MockAction(result=MockResult())
        params = MockParams()

        await machine.run(empty_context, mock_action, params)
        await machine.run(empty_context, mock_action, params)

        assert mock_action.call_count == 2
        assert mock_action.last_params is params

    @pytest.mark.anyio
    async def test_run_mock_action_with_side_effect(self, machine: ActionTestMachine, empty_context: Context) -> None:
        """side_effect is used instead of a fixed result."""
        def side_effect(p):
            return MockResult()

        mock_action = MockAction(side_effect=side_effect)
        params = MockParams()

        result = await machine.run(empty_context, mock_action, params)

        assert isinstance(result, MockResult)
        assert mock_action.call_count == 1


# ======================================================================
# TESTS: run() with real action and mocks
# ======================================================================
class TestRunWithRealAction:
    @pytest.mark.anyio
    async def test_real_action_gets_mocks_from_factory(self, machine_with_mocks: ActionTestMachine, empty_context: Context) -> None:
        """Dependencies from mocks are injected into the action via box.resolve."""
        action = CapturingAction()
        params = MockParams()

        await machine_with_mocks.run(empty_context, action, params)

        assert action.captured == "mocked_string"

    @pytest.mark.anyio
    async def test_real_action_without_mocks_uses_default(self, machine: ActionTestMachine, empty_context: Context) -> None:
        """Without mocks, the default constructor is used."""
        action = ActionWithDeps()
        params = MockParams()

        result = await machine.run(empty_context, action, params)

        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_logger_passed_to_real_action(self, machine: ActionTestMachine, empty_context: Context) -> None:
        """Logger is passed to the real action and works."""
        action = CapturingAction()
        params = MockParams()

        await machine.run(empty_context, action, params)

        # Should have two log calls: debug and info
        assert machine._log_coordinator.emit.await_count >= 2
        # Check that the scope contains the correct mode
        first_call = machine._log_coordinator.emit.call_args_list[0]
        scope = first_call.kwargs["scope"]
        assert scope["mode"] == "test"  # from machine fixture
        assert scope["action"].endswith("CapturingAction")
        assert scope["aspect"] == "summary"


# ======================================================================
# TESTS: _prepare_mock
# ======================================================================
class TestPrepareMock:
    def test_prepare_mock_with_mock_action(self, machine: ActionTestMachine) -> None:
        """MockAction is returned as is."""
        mock = MockAction(result=MockResult())
        prepared = machine._prepare_mock(mock)
        assert prepared is mock

    def test_prepare_mock_with_base_action(self, machine: ActionTestMachine) -> None:
        """BaseAction is returned as is."""
        action = RealAction()
        prepared = machine._prepare_mock(action)
        assert prepared is action

    def test_prepare_mock_with_callable(self, machine: ActionTestMachine) -> None:
        """Callable is wrapped in MockAction with side_effect."""
        def func(p):
            return MockResult()

        prepared = machine._prepare_mock(func)
        assert isinstance(prepared, MockAction)
        assert prepared.side_effect is func

    def test_prepare_mock_with_base_result(self, machine: ActionTestMachine) -> None:
        """BaseResult is wrapped in MockAction with result."""
        result = MockResult()
        prepared = machine._prepare_mock(result)
        assert isinstance(prepared, MockAction)
        assert prepared.result is result

    def test_prepare_mock_with_other_object(self, machine: ActionTestMachine) -> None:
        """Any other object is returned as is."""
        obj = object()
        prepared = machine._prepare_mock(obj)
        assert prepared is obj


# ======================================================================
# TESTS: build_factory
# ======================================================================
class TestBuildFactory:
    def test_build_factory_returns_dependency_factory(self, machine: ActionTestMachine) -> None:
        """build_factory creates a DependencyFactory."""
        factory = machine.build_factory(ActionWithDeps)
        assert isinstance(factory, DependencyFactory)

    @pytest.mark.anyio
    async def test_build_factory_uses_mocks(self, machine_with_mocks: ActionTestMachine, empty_context: Context) -> None:
        """
        build_factory creates a factory with mocks.
        Verified by actually running the action.
        """
        # Replace log coordinator with a mock directly in the test
        mock_coord = AsyncMock(spec=LogCoordinator)
        machine_with_mocks._log_coordinator = mock_coord

        action = CapturingAction()
        params = MockParams()

        await machine_with_mocks.run(empty_context, action, params)

        assert action.captured == "mocked_string"
        # Check that mode from constructor ended up in logs
        mock_coord.emit.assert_awaited()
        # Get the first call
        call_args = mock_coord.emit.call_args
        scope = call_args.kwargs["scope"]
        assert scope["mode"] == "testing_mode"  # from machine_with_mocks fixture

    @pytest.mark.anyio
    async def test_build_factory_respects_external_resources(self, machine: ActionTestMachine) -> None:
        """external_resources have priority over mocks."""
        # Create a machine with a mock for str
        mocks = {str: "mocked"}
        test_machine = ActionTestMachine(mocks=mocks, mode="test")

        # Pass external_resources with a different value via the run method's resources parameter.
        # The new architecture uses box.resolve which checks the resources dictionary.
        # We'll test via _run_internal.
        external = {str: "external"}
        action = RealAction()
        params = MockParams()
        context = Context()

        # We need to call _run_internal to pass resources.
        await test_machine._run_internal(
            context, action, params, resources=external, connections=None, nested_level=0
        )
        # The action captured the resolved value.
        assert action.captured == "external"
