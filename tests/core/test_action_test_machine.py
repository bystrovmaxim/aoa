# tests/core/test_action_test_machine.py
from unittest.mock import Mock

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
    captured = None

    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        self.captured = deps.get(str)
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="")
@depends(int)
class ActionWithDeps(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class ActionWithStrDep(BaseAction[MockParams, MockResult]):
    """Действие с зависимостью str — для проверки build_factory с моками."""
    captured = None

    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        # Сохраняем полученную зависимость для проверки в тесте
        ActionWithStrDep.captured = deps.get(str)
        return MockResult()

@CheckRoles(CheckRoles.NONE, desc="")
@depends(str)
class CapturingAction(BaseAction[MockParams, MockResult]):
    captured = None

    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        self.captured = deps.get(str)
        return MockResult()

# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------
@pytest.fixture
def empty_context():
    return Context()

@pytest.fixture
def machine(empty_context):
    return ActionTestMachine(ctx=empty_context)

@pytest.fixture
def machine_with_mocks():
    mocks = {
        str: "mocked_string",
        int: MockAction(result=MockResult()),
        list: lambda p: ["called"],
    }
    return ActionTestMachine(mocks=mocks)

# ======================================================================
# ТЕСТЫ: run() с MockAction
# ======================================================================
class TestRunWithMockAction:
    @pytest.mark.anyio
    async def test_run_mock_action_directly(self, machine):
        mock_action = MockAction(result=MockResult())
        params = MockParams()
        original_run = mock_action.run
        mock_action.run = Mock(wraps=original_run)
        result = await machine.run(mock_action, params)
        assert mock_action.run.called
        assert mock_action.run.call_args[0][0] is params
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_run_mock_action_tracks_calls(self, machine):
        mock_action = MockAction(result=MockResult())
        params = MockParams()
        await machine.run(mock_action, params)
        await machine.run(mock_action, params)
        assert mock_action.call_count == 2
        assert mock_action.last_params is params

    @pytest.mark.anyio
    async def test_run_mock_action_with_side_effect(self, machine):
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
    async def test_real_action_gets_mocks_from_factory(self, machine_with_mocks):
        action = CapturingAction()
        params = MockParams()
        await machine_with_mocks.run(action, params)
        assert action.captured == "mocked_string"

    @pytest.mark.anyio
    async def test_real_action_without_mocks_uses_default(self, machine):
        """Без моков int() создаётся через конструктор (== 0)."""
        action = ActionWithDeps()
        params = MockParams()
        result = await machine.run(action, params)
        assert isinstance(result, MockResult)

# ======================================================================
# ТЕСТЫ: _prepare_mock
# ======================================================================
class TestPrepareMock:
    def test_prepare_mock_with_mock_action(self, machine):
        mock = MockAction(result=MockResult())
        prepared = machine._prepare_mock(mock)
        assert prepared is mock

    def test_prepare_mock_with_base_action(self, machine):
        action = RealAction()
        prepared = machine._prepare_mock(action)
        assert prepared is action

    def test_prepare_mock_with_callable(self, machine):
        def func(p):
            return MockResult()

        prepared = machine._prepare_mock(func)
        assert isinstance(prepared, MockAction)
        assert prepared.side_effect is func

    def test_prepare_mock_with_base_result(self, machine):
        result = MockResult()
        prepared = machine._prepare_mock(result)
        assert isinstance(prepared, MockAction)
        assert prepared.result is result

    def test_prepare_mock_with_other_object(self, machine):
        obj = object()
        prepared = machine._prepare_mock(obj)
        assert prepared is obj

# ======================================================================
# ТЕСТЫ: build_factory
# ======================================================================
class TestBuildFactory:
    def test_build_factory_returns_dependency_factory(self, machine):
        factory = machine.build_factory(ActionWithDeps)
        assert isinstance(factory, DependencyFactory)

    @pytest.mark.anyio
    async def test_build_factory_uses_mocks(self, machine_with_mocks):
        """
        build_factory создаёт фабрику с моками.
        Проверяем через реальный запуск действия — фабрика используется
        внутри run(), и мок str должен дойти до deps.get(str).
        """
        ActionWithStrDep.captured = None
        action = ActionWithStrDep()
        params = MockParams()
        await machine_with_mocks.run(action, params)
        assert ActionWithStrDep.captured == "mocked_string"