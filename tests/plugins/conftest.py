"""
Фикстуры и тестовые плагины для тестирования PluginCoordinator.
Все тестовые плагины вынесены сюда для переиспользования.
"""

import asyncio
from unittest.mock import Mock

import pytest

from action_machine.Context.context import context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Plugins.Decorators import on
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent

# ======================================================================
# ТЕСТОВЫЕ ПЛАГИНЫ
# ======================================================================


class PluginTestBase(Plugin):
    """
    Базовый тестовый плагин.

    Предоставляет:
    - Имя плагина для идентификации
    - Счетчик вызовов в состоянии
    - Список вызванных обработчиков для проверки
    """

    def __init__(self, name="test"):
        self.name = name
        self.initial_state = {"counter": 0}
        self.handlers_called = []

    def get_initial_state(self):
        """Возвращает копию начального состояния."""
        return self.initial_state.copy()


class SimplePlugin(PluginTestBase):
    """
    Плагин с одним обработчиком для тестирования базовых сценариев.

    Подписан на:
    - test_event (любой класс действия)
    """

    @on("test_event", ".*", ignore_exceptions=False)
    async def handle_test(self, state, event):
        """Простой обработчик, увеличивающий счетчик."""
        self.handlers_called.append(("handle_test", event.event_name))
        state["counter"] = state.get("counter", 0) + 1
        return state


class MultiHandlerPlugin(PluginTestBase):
    """
    Плагин с несколькими обработчиками для тестирования фильтрации.

    Подписан на:
    - event1 (любой класс)
    - event2 (любой класс)
    - event.* (любой класс) — регулярное выражение
    """

    @on("event1", ".*", ignore_exceptions=False)
    async def handle_event1(self, state, event):
        """Обработчик для event1."""
        self.handlers_called.append(("event1", event.event_name))
        state["last"] = "event1"
        return state

    @on("event2", ".*", ignore_exceptions=False)
    async def handle_event2(self, state, event):
        """Обработчик для event2."""
        self.handlers_called.append(("event2", event.event_name))
        state["last"] = "event2"
        return state

    @on("event.*", ".*", ignore_exceptions=False)
    async def handle_any_event(self, state, event):
        """
        Обработчик для любых событий, начинающихся с 'event'.
        Использует регулярное выражение.
        """
        self.handlers_called.append(("any", event.event_name))
        state["any"] = True
        return state


class ClassFilterPlugin(PluginTestBase):
    """
    Плагин с фильтрацией по классу действия.

    Подписан на:
    - любые события для классов, заканчивающихся на OrderAction
    - любые события для классов, заканчивающихся на PaymentAction
    """

    @on(".*", ".*OrderAction", ignore_exceptions=False)
    async def handle_order(self, state, event):
        """Обработчик для действий, связанных с заказами."""
        self.handlers_called.append(("order", event.action_name))
        state["order"] = True
        return state

    @on(".*", ".*PaymentAction", ignore_exceptions=False)
    async def handle_payment(self, state, event):
        """Обработчик для действий, связанных с платежами."""
        self.handlers_called.append(("payment", event.action_name))
        state["payment"] = True
        return state


class IgnoreExceptionsPlugin(PluginTestBase):
    """
    Плагин для тестирования ignore_exceptions.

    Подписан на:
    - test_event с ignore_exceptions=True
    - critical_event с ignore_exceptions=False
    """

    @on("test_event", ".*", ignore_exceptions=True)
    async def handle_ignored(self, state, event):
        """Обработчик, который всегда падает, но исключение игнорируется."""
        self.handlers_called.append(("ignored", event.event_name))
        raise ValueError("Это исключение будет проигнорировано")

    @on("critical_event", ".*", ignore_exceptions=False)
    async def handle_critical(self, state, event):
        """Обработчик, который падает, и исключение пробрасывается."""
        self.handlers_called.append(("critical", event.event_name))
        raise RuntimeError("Это исключение НЕ будет проигнорировано")


class SlowPlugin(PluginTestBase):
    """
    Плагин с медленным обработчиком для тестов конкурентности.

    Подписан на slow_event.
    Обработчик спит 0.1 секунды перед возвратом.
    """

    @on("slow_event", ".*", ignore_exceptions=False)
    async def handle_slow(self, state, event):
        """Медленный обработчик с задержкой."""
        self.handlers_called.append(("slow", event.event_name))
        await asyncio.sleep(0.1)  # 100ms задержки
        state["slow_done"] = True
        return state


class CustomStatePlugin(PluginTestBase):
    """
    Плагин с кастомным начальным состоянием.

    Возвращает состояние со списком и числовым значением.
    """

    def get_initial_state(self):
        """Возвращает сложное начальное состояние."""
        return {"value": 100, "items": [1, 2, 3]}


# ======================================================================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ДЛЯ ТЕСТОВ
# ======================================================================


class MockAction(BaseAction):
    """Мок действия для тестов с фиксированным именем класса."""

    _full_class_name = "test_plugin.MockAction"


class MockParams(BaseParams):
    """Мок параметров действия."""

    pass


class MockResult(BaseResult):
    """Мок результата действия."""

    pass


# ======================================================================
# ФИКСТУРЫ
# ======================================================================


@pytest.fixture
def simple_plugin():
    """Фикстура, возвращающая новый экземпляр SimplePlugin."""
    return SimplePlugin()


@pytest.fixture
def multi_handler_plugin():
    """Фикстура, возвращающая новый экземпляр MultiHandlerPlugin."""
    return MultiHandlerPlugin()


@pytest.fixture
def class_filter_plugin():
    """Фикстура, возвращающая новый экземпляр ClassFilterPlugin."""
    return ClassFilterPlugin()


@pytest.fixture
def ignore_exceptions_plugin():
    """Фикстура, возвращающая новый экземпляр IgnoreExceptionsPlugin."""
    return IgnoreExceptionsPlugin()


@pytest.fixture
def slow_plugin():
    """Фикстура, возвращающая новый экземпляр SlowPlugin."""
    return SlowPlugin()


@pytest.fixture
def mock_action():
    """Фикстура, возвращающая новый экземпляр MockAction."""
    return MockAction()


@pytest.fixture
def mock_params():
    """Фикстура, возвращающая новый экземпляр MockParams."""
    return MockParams()


@pytest.fixture
def mock_factory():
    """Фикстура, возвращающая мок DependencyFactory."""
    return Mock(spec=DependencyFactory)


@pytest.fixture
def mock_context():
    """Фикстура, возвращающая мок Context."""
    return Mock(spec=context)


@pytest.fixture
def event_factory():
    """
    Фабрика для создания PluginEvent с значениями по умолчанию.

    Позволяет в тестах создавать события, переопределяя только нужные поля.
    """

    def _create_event(**kwargs):
        default_event = PluginEvent(
            event_name="test_event",
            action_name="TestAction",
            params=MockParams(),
            state_aspect={},
            is_summary=False,
            deps=Mock(spec=DependencyFactory),
            context=Mock(spec=context),
            result=None,
            duration=None,
            nest_level=0,
        )
        # Обновляем значения по умолчанию переданными kwargs
        for key, value in kwargs.items():
            setattr(default_event, key, value)
        return default_event

    return _create_event
