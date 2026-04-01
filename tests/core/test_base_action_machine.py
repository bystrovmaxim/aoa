# tests/core/test_base_action_machine.py
"""
Тесты для BaseActionMachine и синхронного выполнения через SyncActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

SyncActionProductMachine.run():
    - Вызов вне event loop — действие выполняется и возвращает результат.
    - Вызов внутри работающего event loop — RuntimeError от asyncio.run().

BaseActionMachine:
    - Абстрактный класс — нельзя создать экземпляр напрямую.
    - _run_internal по умолчанию бросает NotImplementedError.
"""

import warnings

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_action_machine import BaseActionMachine
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.sync_action_product_machine import SyncActionProductMachine
from action_machine.core.tools_box import ToolsBox

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели и действия
# ═════════════════════════════════════════════════════════════════════════════


class MockParams(BaseParams):
    """Пустые параметры для тестового действия."""
    pass


class MockResult(BaseResult):
    """Пустой результат для тестового действия."""
    pass


@meta(description="Минимальное действие для тестирования синхронного выполнения")
@check_roles(ROLE_NONE)
class SimpleAction(BaseAction[MockParams, MockResult]):
    """Минимальное действие — один summary-аспект, без зависимостей."""

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, object],
    ) -> MockResult:
        """Возвращает пустой MockResult."""
        return MockResult()


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: SyncActionProductMachine.run() — синхронное выполнение
# ═════════════════════════════════════════════════════════════════════════════


class TestSyncRun:
    """
    Тесты синхронного run() через SyncActionProductMachine.

    SyncActionProductMachine.run() вызывает asyncio.run() внутри.
    Работает только вне активного event loop.
    """

    def test_outside_event_loop_returns_result(self) -> None:
        """
        Проверяет, что синхронный run() вне event loop выполняет действие:

        1. SyncActionProductMachine.run() создаёт event loop через asyncio.run().
        2. Действие проходит конвейер (проверка ролей, summary-аспект).
        3. Возвращает MockResult синхронно.

        Это основной сценарий использования: CLI-скрипты, Celery, Django без async.
        """
        machine = SyncActionProductMachine(mode="test")
        result = machine.run(Context(), SimpleAction(), MockParams())
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_inside_event_loop_raises_runtime_error(self) -> None:
        """
        Проверяет, что синхронный run() внутри event loop бросает RuntimeError:

        asyncio.run() не может быть вызван из уже работающего event loop.
        Это защита от случайного использования SyncActionProductMachine
        в async-контексте (FastAPI endpoint, aiohttp handler).

        В async-контексте нужно использовать ActionProductMachine.
        """
        machine = SyncActionProductMachine(mode="test")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(
                RuntimeError,
                match="cannot be called from a running event loop",
            ):
                machine.run(Context(), SimpleAction(), MockParams())


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: BaseActionMachine — абстрактный контракт
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseActionMachine:
    """Тесты абстрактного базового класса BaseActionMachine."""

    def test_cannot_instantiate_directly(self):
        """
        Проверяет, что BaseActionMachine нельзя создать напрямую:

        BaseActionMachine — абстрактный класс с абстрактным методом run().
        Попытка создать экземпляр — TypeError.
        """
        with pytest.raises(TypeError):
            BaseActionMachine()  # type: ignore[abstract]

    @pytest.mark.anyio
    async def test_run_internal_raises_not_implemented(self):
        """
        Проверяет, что _run_internal() по умолчанию бросает NotImplementedError:

        Конкретные машины (ActionProductMachine, SyncActionProductMachine)
        переопределяют _run_internal(). Если не переопределили — ошибка.
        """
        # Создаём минимальный конкретный подкласс только с run()
        class MinimalMachine(BaseActionMachine):
            def run(self, context, action, params, connections=None):
                pass

        machine = MinimalMachine()
        with pytest.raises(NotImplementedError):
            await machine._run_internal(
                context=Context(),
                action=SimpleAction(),
                params=MockParams(),
                resources=None,
                connections=None,
                nested_level=0,
                rollup=False,
            )
