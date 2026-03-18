# tests/core/test_base_action_machine.py
"""
Тесты BaseActionMachine.sync_run.

Покрываем строки 87-98:
  - Нормальный вызов вне event loop.
  - Ошибка при вызове внутри event loop.

Строгая типизация: все параметры и возвращаемые значения аннотированы.
state заменён с dict на BaseState.
"""

import warnings

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory


################################################################################
# Вспомогательные классы
################################################################################


class MockParams(BaseParams):
    """Пустые параметры для тестового действия."""

    pass


class MockResult(BaseResult):
    """Пустой результат для тестового действия."""

    pass


@CheckRoles(CheckRoles.NONE, desc="")
class SimpleAction(BaseAction[MockParams, MockResult]):
    """
    Минимальное действие для проверки sync_run.

    Возвращает MockResult без побочных эффектов.
    """

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, object],
    ) -> MockResult:
        """
        Основной аспект действия.

        Аргументы:
            params:      входные параметры действия.
            state:       состояние конвейера аспектов.
            deps:        фабрика зависимостей.
            connections: словарь подключений.

        Возвращает:
            MockResult: пустой результат.
        """
        return MockResult()


################################################################################
# Тесты
################################################################################


class TestSyncRun:
    """Тесты синхронной обёртки sync_run."""

    def test_sync_run_outside_event_loop_returns_result(self) -> None:
        """
        sync_run вне async-контекста выполняет действие и возвращает результат.

        Проверяет:
            - Вызов sync_run без активного event loop завершается успешно.
            - Возвращённый объект является экземпляром MockResult.
        """
        machine: ActionProductMachine = ActionProductMachine(Context())
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()

        result: MockResult = machine.sync_run(action, params)

        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_sync_run_inside_event_loop_raises_runtime_error(self) -> None:
        """
        sync_run внутри работающего event loop бросает RuntimeError.

        Из-за особенности реализации except RuntimeError в sync_run
        наружу вылетает сообщение от asyncio.run().

        Warning о невызванной корутине подавляется — это ожидаемое поведение.

        Проверяет:
            - RuntimeError с сообщением "cannot be called from a running event loop".
        """
        machine: ActionProductMachine = ActionProductMachine(Context())
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(
                RuntimeError,
                match="cannot be called from a running event loop",
            ):
                machine.sync_run(action, params)