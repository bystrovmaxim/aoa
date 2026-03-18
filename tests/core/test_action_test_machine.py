# tests/core/test_action_test_machine.py
"""
Тесты ActionTestMachine — тестовой машины действий с поддержкой моков.

Проверяем:
- Запуск MockAction напрямую (без аспектов)
- Запуск реальных действий с моками зависимостей
- Подготовку моков (_prepare_mock)
- Метод build_factory
- Передачу mode и log_coordinator (изменения в конструкторе)
- По умолчанию mode="test"
"""

from unittest.mock import AsyncMock, Mock

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.ActionTestMachine import ActionTestMachine
from action_machine.Core.AspectMethod import depends, summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.MockAction import MockAction
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.Logging.log_coordinator import LogCoordinator


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class RealAction(BaseAction[MockParams, MockResult]):
    """Реальное действие с зависимостью str."""
    captured = None
    log_called = False

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        deps: DependencyFactory,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        self.captured = deps.get(str)
        # Проверяем, что логер работает
        await log.info("Summary executed", action="RealAction")
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
        deps: DependencyFactory,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        return MockResult()


@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class CapturingAction(BaseAction[MockParams, MockResult]):
    """Действие, сохраняющее полученную зависимость и вызывающее лог."""
    captured = None
    log_messages = []

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: dict,
        deps: DependencyFactory,
        connections: dict,
        log: ActionBoundLogger,
    ) -> MockResult:
        self.captured = deps.get(str)
        await log.debug("Debug from CapturingAction")
        await log.info("Info from CapturingAction")
        return MockResult()


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------
@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def machine(empty_context: Context) -> ActionTestMachine:
    """Тестовая машина с режимом по умолчанию (test) и мок-координатором логов."""
    mock_log_coordinator = AsyncMock(spec=LogCoordinator)
    return ActionTestMachine(
        ctx=empty_context,
        mode="test",
        log_coordinator=mock_log_coordinator,
    )


@pytest.fixture
def machine_with_mocks() -> ActionTestMachine:
    """Машина с предустановленными моками."""
    mocks = {
        str: "mocked_string",
        int: MockAction(result=MockResult()),
        list: lambda p: ["called"],
    }
    return ActionTestMachine(mocks=mocks, mode="testing_mode")


# ======================================================================
# ТЕСТЫ: Конструктор
# ======================================================================
class TestConstructor:
    def test_default_mode_is_test(self, empty_context: Context) -> None:
        """По умолчанию mode = 'test'."""
        machine = ActionTestMachine(ctx=empty_context)
        assert machine._mode == "test"

    def test_custom_mode_passed_to_parent(self, empty_context: Context) -> None:
        """Переданный mode попадает в родительский класс."""
        machine = ActionTestMachine(ctx=empty_context, mode="custom_mode")
        assert machine._mode == "custom_mode"

    def test_log_coordinator_passed_to_parent(self, empty_context: Context) -> None:
        """Переданный log_coordinator используется в родителе."""
        mock_coord = AsyncMock(spec=LogCoordinator)
        machine = ActionTestMachine(ctx=empty_context, log_coordinator=mock_coord)
        assert machine._log_coordinator is mock_coord


# ======================================================================
# ТЕСТЫ: run() с MockAction
# ======================================================================
class TestRunWithMockAction:
    @pytest.mark.anyio
    async def test_run_mock_action_directly(self, machine: ActionTestMachine) -> None:
        """MockAction запускается напрямую, минуя аспекты."""
        mock_action = MockAction(result=MockResult())
        params = MockParams()
        original_run = mock_action.run
        mock_action.run = Mock(wraps=original_run)

        result = await machine.run(mock_action, params)

        mock_action.run.assert_called_once_with(params)
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_mock_action_tracks_calls(self, machine: ActionTestMachine) -> None:
        """MockAction подсчитывает вызовы и сохраняет параметры."""
        mock_action = MockAction(result=MockResult())
        params = MockParams()

        await machine.run(mock_action, params)
        await machine.run(mock_action, params)

        assert mock_action.call_count == 2
        assert mock_action.last_params is params

    @pytest.mark.anyio
    async def test_run_mock_action_with_side_effect(self, machine: ActionTestMachine) -> None:
        """side_effect используется вместо фиксированного результата."""
        def side_effect(p):
            return MockResult()

        mock_action = MockAction(side_effect=side_effect)
        params = MockParams()

        result = await machine.run(mock_action, params)

        assert isinstance(result, MockResult)
        assert mock_action.call_count == 1


# ======================================================================
# ТЕСТЫ: run() с реальным действием и моками
# ======================================================================
class TestRunWithRealAction:
    @pytest.mark.anyio
    async def test_real_action_gets_mocks_from_factory(self, machine_with_mocks: ActionTestMachine) -> None:
        """Зависимости из моков подставляются в действие."""
        action = CapturingAction()
        params = MockParams()

        await machine_with_mocks.run(action, params)

        assert action.captured == "mocked_string"

    @pytest.mark.anyio
    async def test_real_action_without_mocks_uses_default(self, machine: ActionTestMachine) -> None:
        """Без моков используется конструктор по умолчанию."""
        action = ActionWithDeps()
        params = MockParams()

        result = await machine.run(action, params)

        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_logger_passed_to_real_action(self, machine: ActionTestMachine) -> None:
        """В реальное действие передаётся логер и работает."""
        action = CapturingAction()
        params = MockParams()

        await machine.run(action, params)

        # Должны быть два вызова лога: debug и info
        assert machine._log_coordinator.emit.await_count >= 2
        # Проверим, что scope содержит правильный mode
        first_call = machine._log_coordinator.emit.call_args_list[0]
        scope = first_call.kwargs["scope"]
        assert scope["mode"] == "test"  # из фикстуры machine
        assert scope["action"].endswith("CapturingAction")
        assert scope["aspect"] == "summary"


# ======================================================================
# ТЕСТЫ: _prepare_mock
# ======================================================================
class TestPrepareMock:
    def test_prepare_mock_with_mock_action(self, machine: ActionTestMachine) -> None:
        """MockAction возвращается как есть."""
        mock = MockAction(result=MockResult())
        prepared = machine._prepare_mock(mock)
        assert prepared is mock

    def test_prepare_mock_with_base_action(self, machine: ActionTestMachine) -> None:
        """BaseAction возвращается как есть."""
        action = RealAction()
        prepared = machine._prepare_mock(action)
        assert prepared is action

    def test_prepare_mock_with_callable(self, machine: ActionTestMachine) -> None:
        """Callable оборачивается в MockAction с side_effect."""
        def func(p):
            return MockResult()

        prepared = machine._prepare_mock(func)
        assert isinstance(prepared, MockAction)
        assert prepared.side_effect is func

    def test_prepare_mock_with_base_result(self, machine: ActionTestMachine) -> None:
        """BaseResult оборачивается в MockAction с result."""
        result = MockResult()
        prepared = machine._prepare_mock(result)
        assert isinstance(prepared, MockAction)
        assert prepared.result is result

    def test_prepare_mock_with_other_object(self, machine: ActionTestMachine) -> None:
        """Любой другой объект возвращается как есть."""
        obj = object()
        prepared = machine._prepare_mock(obj)
        assert prepared is obj


# ======================================================================
# ТЕСТЫ: build_factory
# ======================================================================
class TestBuildFactory:
    def test_build_factory_returns_dependency_factory(self, machine: ActionTestMachine) -> None:
        """build_factory создаёт DependencyFactory."""
        factory = machine.build_factory(ActionWithDeps)
        assert isinstance(factory, DependencyFactory)

    @pytest.mark.anyio
    async def test_build_factory_uses_mocks(self, machine_with_mocks: ActionTestMachine) -> None:
        """
        build_factory создаёт фабрику с моками.
        Проверяем через реальный запуск действия.
        """
        # Подменим координатор логов на мок прямо в тесте
        mock_coord = AsyncMock(spec=LogCoordinator)
        machine_with_mocks._log_coordinator = mock_coord

        action = CapturingAction()
        params = MockParams()

        await machine_with_mocks.run(action, params)

        assert action.captured == "mocked_string"
        # Проверим, что mode из конструктора попал в логи
        mock_coord.emit.assert_awaited()
        # Берём первый вызов
        call_args = mock_coord.emit.call_args
        scope = call_args.kwargs["scope"]
        assert scope["mode"] == "testing_mode"  # из фикстуры machine_with_mocks

    def test_build_factory_respects_external_resources(self, machine: ActionTestMachine) -> None:
        """external_resources имеют приоритет над моками."""
        # Создадим машину с моком для str
        mocks = {str: "mocked"}
        test_machine = ActionTestMachine(mocks=mocks, mode="test")

        # Передаём external_resources с другим значением
        external = {str: "external"}
        factory = test_machine._get_factory(RealAction, external_resources=external)

        # Должен вернуться external, а не mocked
        assert factory.get(str) == "external"