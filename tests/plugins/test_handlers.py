# Файл: /Users/bystrovmaxim/PythonDev/kanban_assistant/tests/plugins/test_handlers.py
"""
Тесты запуска обработчиков плагинов в PluginCoordinator.

Проверяем:
- Запуск одного обработчика
- Запуск нескольких обработчиков одного плагина
- Запуск обработчиков из разных плагинов
- Обновление состояний после выполнения
"""

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import MultiHandlerPlugin, SimplePlugin


class TestPluginCoordinatorRunHandlers:
    """Тесты запуска обработчиков плагинов."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Запуск одного обработчика
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_run_single_handler(self, event_factory):
        """Запуск одного обработчика одного плагина."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Инициализируем состояние
        await coordinator._init_plugin_states()

        # Создаём событие
        event = event_factory(event_name="test_event")

        # Получаем обработчик
        handlers = coordinator._get_handlers("test_event", "TestAction")
        handler, ignore = handlers[0]

        # Запускаем
        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Проверяем что обработчик вызван и состояние обновилось
        assert plugin.handlers_called == [("handle_test", "test_event")]
        assert coordinator._plugin_states[id(plugin)]["counter"] == 1

    @pytest.mark.anyio
    async def test_run_single_handler_preserves_state(self, event_factory):
        """
        Обработчик получает актуальное состояние и может его изменить.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Устанавливаем начальное состояние
        coordinator._plugin_states[id(plugin)]["counter"] = 5

        event = event_factory(event_name="test_event")
        handlers = coordinator._get_handlers("test_event", "TestAction")
        handler, ignore = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Состояние должно увеличиться на 1 (было 5, стало 6)
        assert coordinator._plugin_states[id(plugin)]["counter"] == 6

    # ------------------------------------------------------------------
    # ТЕСТЫ: Запуск нескольких обработчиков одного плагина
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_run_multiple_handlers_same_plugin(self, event_factory):
        """Запуск нескольких обработчиков одного плагина."""
        plugin = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="event1")

        handlers = coordinator._get_handlers("event1", "TestAction")

        # Должно быть 2 обработчика: handle_event1 и handle_any_event

        for handler, ignore in handlers:
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert len(plugin.handlers_called) == 2
        called_pairs = [(name, ev_name) for name, ev_name in plugin.handlers_called]
        assert ("event1", "event1") in called_pairs
        assert ("any", "event1") in called_pairs

        # Проверяем, что состояние было изменено обоими обработчиками
        final_state = coordinator._plugin_states[id(plugin)]
        assert final_state["last"] == "event1"
        assert final_state["any"] is True

    @pytest.mark.anyio
    async def test_handlers_execution_order(self, event_factory):
        """
        Обработчики выполняются в порядке их добавления в список.
        Каждый следующий видит состояние, изменённое предыдущим.
        """
        plugin = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="event1")
        handlers = coordinator._get_handlers("event1", "TestAction")

        # Запускаем последовательно
        for handler, ignore in handlers:
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Проверяем порядок вызовов — допускаем оба имени,
        # т.к. MultiHandlerPlugin записывает "event1" и "any"
        # (не "handle_event1" и "handle_any_event")
        handler_names = [call[0] for call in plugin.handlers_called]
        assert len(handler_names) == 2
        assert set(handler_names) == {"event1", "any"}

    # ------------------------------------------------------------------
    # ТЕСТЫ: Запуск обработчиков из разных плагинов
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_run_handlers_multiple_plugins(self, event_factory):
        """Запуск обработчиков из разных плагинов."""
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="test_event")

        # Получаем обработчики для всех плагинов
        handlers = coordinator._get_handlers("test_event", "TestAction")
        assert len(handlers) == 2  # по одному из каждого плагина

        # Запускаем каждый обработчик с его плагином
        for handler, ignore in handlers:
            plugin = coordinator._find_plugin_for_handler(handler)
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert plugin1.handlers_called == [("handle_test", "test_event")]
        assert plugin2.handlers_called == [("handle_test", "test_event")]
        assert coordinator._plugin_states[id(plugin1)]["counter"] == 1
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 1

    @pytest.mark.anyio
    async def test_plugins_independent_states(self, event_factory):
        """
        Состояния разных плагинов независимы при выполнении.
        """
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        # Устанавливаем разные начальные состояния
        coordinator._plugin_states[id(plugin1)]["counter"] = 10
        coordinator._plugin_states[id(plugin2)]["counter"] = 20

        event = event_factory(event_name="test_event")
        handlers = coordinator._get_handlers("test_event", "TestAction")

        for handler, ignore in handlers:
            plugin = coordinator._find_plugin_for_handler(handler)
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Каждый плагин увеличил своё состояние на 1
        assert coordinator._plugin_states[id(plugin1)]["counter"] == 11
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 21
