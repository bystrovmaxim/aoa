# tests/core/test_base_action_machine.py
"""
Тесты для BaseActionMachine.sync_run.

Проверяется:
- Нормальный вызов sync_run вне event loop — действие выполняется
  и возвращает результат.
- Вызов sync_run внутри уже запущенного event loop — RuntimeError
  с сообщением от asyncio.run().

sync_run — синхронная обёртка для использования вне асинхронного контекста
(скрипты командной строки, Celery-задачи, Django-вьюхи без async).
Создаёт новый event loop, выполняет действие и возвращает результат.
"""

import warnings

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox

################################################################################
# Вспомогательные классы
################################################################################


class MockParams(BaseParams):
    """Пустые параметры для тестового действия."""
    pass


class MockResult(BaseResult):
    """Пустой результат для тестового действия."""
    pass


@meta(description="Минимальное действие для тестирования sync_run")
@CheckRoles(CheckRoles.NONE, desc="")
class SimpleAction(BaseAction[MockParams, MockResult]):
    """
    Минимальное действие для тестирования sync_run.

    Возвращает MockResult без побочных эффектов. Содержит только
    summary-аспект, что является минимальной допустимой конфигурацией
    для выполнения через машину.
    """

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, object],
    ) -> MockResult:
        """
        Единственный аспект действия.

        Аргументы:
            params: входные параметры.
            state: состояние конвейера аспектов.
            box: ToolsBox (предоставляет логирование и зависимости).
            connections: словарь соединений.

        Возвращает:
            MockResult: пустой результат.
        """
        return MockResult()


################################################################################
# Тесты
################################################################################


class TestSyncRun:
    """Тесты для синхронной обёртки sync_run."""

    def test_sync_run_outside_event_loop_returns_result(self) -> None:
        """
        sync_run вне асинхронного контекста выполняет действие и возвращает результат.

        Проверяется:
            - Вызов sync_run без активного event loop завершается успешно.
            - Возвращённый объект является экземпляром MockResult.
        """
        machine: ActionProductMachine = ActionProductMachine(mode="test")
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()
        context: Context = Context()

        result: MockResult = machine.sync_run(context, action, params)

        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_sync_run_inside_event_loop_raises_runtime_error(self) -> None:
        """
        sync_run внутри работающего event loop вызывает RuntimeError.

        asyncio.run() не может быть вызван из уже запущенного event loop.
        Предупреждение о неожиданной корутине подавляется — оно ожидаемо.

        Проверяется:
            - RuntimeError с сообщением "cannot be called from a running event loop".
        """
        machine: ActionProductMachine = ActionProductMachine(mode="test")
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()
        context: Context = Context()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(
                RuntimeError,
                match="cannot be called from a running event loop",
            ):
                machine.sync_run(context, action, params)
