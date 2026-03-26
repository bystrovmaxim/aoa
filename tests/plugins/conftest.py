# tests/plugins/conftest.py
"""
Фикстуры для тестирования плагинов ActionMachine.

Обеспечивают:
- Моки для действий (MockAction) с актуальной сигнатурой аспектов (ToolsBox).
- Фикстуры для параметров, состояний и результатов.
- Базовые объекты для тестирования событий плагинов (SimplePlugin, SlowPlugin и др.).
- Фикстуры фабрики зависимостей и контекста.
"""

import asyncio
from typing import Any

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.dependencies.dependency_gate import DependencyGate
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent

# ----------------------------------------------------------------------
# Вспомогательные классы данных
# ----------------------------------------------------------------------

class MockParams(BaseParams):
    """Тестовые параметры для действий."""
    pass


class MockResult(BaseResult):
    """Тестовый результат для действий."""
    pass


# ----------------------------------------------------------------------
# Мок-действие для подписок плагинов
# ----------------------------------------------------------------------

@CheckRoles(CheckRoles.NONE, desc="Действие для тестов плагинов")
class MockAction(BaseAction[MockParams, MockResult]):
    """
    Действие-заглушка для проверки работы плагинов.
    Содержит как regular, так и summary аспекты для генерации полного
    набора событий.
    """

    @regular_aspect("Шаг подготовки")
    async def prepare(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> dict:
        return {"prepared": True}

    @summary_aspect("Финальный шаг")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict,
    ) -> MockResult:
        res = MockResult()
        res["status"] = "success"
        res["prepared"] = state.get("prepared")
        return res


# ----------------------------------------------------------------------
# Тестовые плагины
# ----------------------------------------------------------------------

class SimplePlugin(Plugin):
    """Простой плагин, считающий количество вызовов и записывающий их."""

    def __init__(self):
        self.handlers_called: list[tuple[str, str]] = []

    async def get_initial_state(self) -> dict:
        return {"counter": 0}

    @on("test_event", ".*")
    async def handle_test(self, state: dict, event: PluginEvent) -> dict:
        self.handlers_called.append(("handle_test", event.event_name))
        state["counter"] += 1
        return state


class SlowPlugin(Plugin):
    """Плагин с искусственной задержкой для проверки конкурентности."""

    def __init__(self, delay: float = 0.1):
        self.delay = delay
        self.handlers_called: list[tuple[str, str]] = []

    async def get_initial_state(self) -> dict:
        return {"done": False}

    @on("slow_event", ".*")
    async def on_slow(self, state: dict, event: PluginEvent) -> dict:
        await asyncio.sleep(self.delay)
        self.handlers_called.append(("slow", event.event_name))
        state["done"] = True
        return state


class IgnoreExceptionsPlugin(Plugin):
    """Плагин, генерирующий ошибки, для проверки флага ignore_exceptions."""

    def __init__(self):
        self.handlers_called: list[tuple[str, str]] = []

    async def get_initial_state(self) -> dict:
        return {"failed": False}

    @on("test_event", ".*", ignore_exceptions=True)
    async def ignored_handler(self, state: dict, event: PluginEvent) -> dict:
        self.handlers_called.append(("ignored", event.event_name))
        raise ValueError("This exception will be ignored")

    @on("critical_event", ".*", ignore_exceptions=False)
    async def critical_handler(self, state: dict, event: PluginEvent) -> dict:
        self.handlers_called.append(("critical", event.event_name))
        raise RuntimeError("This exception will NOT be ignored")


class MultiHandlerPlugin(Plugin):
    """Плагин с несколькими обработчиками на разные события."""

    def __init__(self):
        self.handlers_called: list[tuple[str, str]] = []

    async def get_initial_state(self) -> dict:
        return {"last": None, "any": False}

    @on("event1", ".*")
    async def handle_event1(self, state: dict, event: PluginEvent) -> dict:
        self.handlers_called.append(("event1", event.event_name))
        state["last"] = "event1"
        return state

    @on(".*", ".*")  # ловит любое событие
    async def handle_any_event(self, state: dict, event: PluginEvent) -> dict:
        self.handlers_called.append(("any", event.event_name))
        state["any"] = True
        return state


class CustomStatePlugin(Plugin):
    """Плагин с кастомным объектом состояния (не словарем)."""

    class MyState:
        def __init__(self):
            self.value = 0
            self.items = []

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, dict):
                return self.value == other.get("value") and self.items == other.get("items")
            if isinstance(other, CustomStatePlugin.MyState):
                return self.value == other.value and self.items == other.items
            return False

    async def get_initial_state(self) -> MyState:
        return self.MyState()

    @on("custom_event", ".*")
    async def on_custom(self, state: MyState, event: PluginEvent) -> MyState:
        state.value = 42
        return state


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------

@pytest.fixture
def mock_action() -> MockAction:
    """Возвращает экземпляр тестового действия."""
    return MockAction()


@pytest.fixture
def mock_params() -> MockParams:
    """Возвращает пустые тестовые параметры."""
    return MockParams()


@pytest.fixture
def mock_state() -> BaseState:
    """Возвращает тестовое состояние."""
    return BaseState({"initial": "data"})


@pytest.fixture
def mock_result() -> MockResult:
    """Возвращает тестовый результат."""
    return MockResult()


@pytest.fixture
def mock_context() -> Context:
    """Возвращает базовый контекст."""
    return Context()


@pytest.fixture
def mock_factory() -> DependencyFactory:
    """Возвращает пустую фабрику зависимостей."""
    gate = DependencyGate()
    gate.freeze()
    return DependencyFactory(gate)


@pytest.fixture
def event_factory(mock_action, mock_params, mock_factory, mock_context):
    """
    Фабрика для генерации объектов PluginEvent.
    Позволяет в тестах гибко создавать события.
    """
    def _create(
        event_name="test_event",
        action_name=None,
        is_summary=False,
        result=None,
        duration=None,
        nest_level=0,
    ) -> PluginEvent:
        return PluginEvent(
            event_name=event_name,
            action_name=action_name or mock_action.get_full_class_name(),
            params=mock_params,
            state_aspect={},
            is_summary=is_summary,
            deps=mock_factory,
            context=mock_context,
            result=result,
            duration=duration,
            nest_level=nest_level,
        )
    return _create
