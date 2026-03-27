# tests/plugins/test_exceptions.py
"""
Тесты обработки исключений в PluginCoordinator.

Проверяется:
- При ignore_exceptions=True ошибка обработчика подавляется молча,
  состояние плагина не обновляется, выполнение действия продолжается.
  Никакого вывода в stdout не производится.
- При ignore_exceptions=False ошибка обработчика пробрасывается наружу
  и прерывает выполнение.
- Кастомные исключения при ignore_exceptions=True подавляются так же.
"""

import pytest

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import IgnoreExceptionsPlugin, MockParams


class TestPluginCoordinatorExceptions:
    """Тесты обработки исключений в обработчиках плагинов."""

    @pytest.mark.anyio
    async def test_ignore_exceptions_true(self, mock_action, mock_factory, mock_context):
        """
        При ignore_exceptions=True ошибка обработчика подавляется молча.

        Состояние плагина не обновляется (остаётся начальным).
        Никакого вывода в stdout не производится — ошибка игнорируется
        без диагностики. Для диагностики используется LogCoordinator
        или callback, переданный в конструктор координатора.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        params = MockParams()

        # Не должно бросить исключение
        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Обработчик был вызван
        assert len(plugin.handlers_called) == 1
        assert plugin.handlers_called[0] == ("ignored", "test_event")

        # Состояние не обновилось (ошибка произошла до return)
        plugin_state = coordinator._plugin_states[id(plugin)]
        assert plugin_state["failed"] is False

    @pytest.mark.anyio
    async def test_ignore_exceptions_false_propagates(self, mock_action, mock_factory, mock_context):
        """
        При ignore_exceptions=False ошибка обработчика пробрасывается наружу.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        params = MockParams()

        with pytest.raises(RuntimeError, match="This exception will NOT be ignored"):
            await coordinator.emit_event(
                event_name="critical_event",
                action=mock_action,
                params=params,
                state_aspect={},
                is_summary=False,
                result=None,
                duration=None,
                factory=mock_factory,
                context=mock_context,
                nest_level=0,
            )

    @pytest.mark.anyio
    async def test_ignore_exceptions_with_custom_exception(self, mock_action, mock_factory, mock_context):
        """
        Кастомные исключения при ignore_exceptions=True подавляются так же,
        как и стандартные. Никакого вывода в stdout не производится.
        """

        from action_machine.plugins.decorators import on
        from action_machine.plugins.plugin import Plugin
        from action_machine.plugins.plugin_event import PluginEvent

        class CustomError(Exception):
            pass

        class CustomIgnorePlugin(Plugin):
            def __init__(self):
                self.handlers_called = []

            async def get_initial_state(self) -> dict:
                return {}

            @on("test_event", ".*", ignore_exceptions=True)
            async def handler(self, state: dict, event: PluginEvent) -> dict:
                self.handlers_called.append(("custom", event.event_name))
                raise CustomError("Custom exception")

        plugin = CustomIgnorePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        params = MockParams()

        # Не должно бросить исключение
        await coordinator.emit_event(
            event_name="test_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Обработчик был вызван
        assert len(plugin.handlers_called) == 1
        assert plugin.handlers_called[0] == ("custom", "test_event")
