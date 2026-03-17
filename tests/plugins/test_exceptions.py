"""
Тесты обработки исключений в плагинах через PluginCoordinator.

Проверяем:
- Игнорирование исключений при ignore_exceptions=True
- Проброс исключений при ignore_exceptions=False
- Смешанные сценарии с разными флагами
- Логирование игнорируемых исключений
"""

import pytest

from action_machine.Plugins.Decorators import on
from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import IgnoreExceptionsPlugin


class TestPluginCoordinatorExceptions:
    """Тесты обработки исключений в плагинах."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: ignore_exceptions = True
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_ignore_exceptions_true(self, capsys, event_factory):
        """
        Исключение игнорируется при ignore_exceptions=True.

        Проверяем:
        - Обработчик вызывается
        - Исключение не пробрасывается наружу
        - Исключение логируется в stdout
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="test_event")

        handlers = coordinator._get_handlers("test_event", "TestAction")
        assert len(handlers) == 1
        handler, ignore = handlers[0]
        assert ignore is True

        # Не должно выбросить исключение
        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Проверяем что обработчик вызывался
        assert plugin.handlers_called == [("ignored", "test_event")]

        # Проверяем что исключение было залогировано
        captured = capsys.readouterr()
        assert "ignored error: Это исключение будет проигнорировано" in captured.out

    @pytest.mark.anyio
    async def test_ignore_exceptions_true_state_not_updated(self, capsys, event_factory):
        """
        При игнорировании исключения состояние плагина не обновляется.

        Обработчик упал, но новое состояние не сохраняется.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Устанавливаем начальное состояние
        coordinator._plugin_states[id(plugin)] = {"counter": 42, "test": "value"}

        event = event_factory(event_name="test_event")
        handlers = coordinator._get_handlers("test_event", "TestAction")
        handler, ignore = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Состояние должно остаться прежним (обработчик не вернул новое)
        assert coordinator._plugin_states[id(plugin)] == {"counter": 42, "test": "value"}

    # ------------------------------------------------------------------
    # ТЕСТЫ: ignore_exceptions = False
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_ignore_exceptions_false(self, event_factory):
        """
        Исключение пробрасывается при ignore_exceptions=False.

        Проверяем:
        - Обработчик вызывается
        - Исключение пробрасывается наружу
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="critical_event")

        handlers = coordinator._get_handlers("critical_event", "TestAction")
        assert len(handlers) == 1
        handler, ignore = handlers[0]
        assert ignore is False

        with pytest.raises(RuntimeError, match="Это исключение НЕ будет проигнорировано"):
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Проверяем что обработчик вызывался до ошибки
        assert plugin.handlers_called == [("critical", "critical_event")]

    @pytest.mark.anyio
    async def test_ignore_exceptions_false_state_not_updated(self, event_factory):
        """
        При пробросе исключения состояние плагина не обновляется.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Устанавливаем начальное состояние
        initial_state = {"counter": 100}
        coordinator._plugin_states[id(plugin)] = initial_state.copy()

        event = event_factory(event_name="critical_event")
        handlers = coordinator._get_handlers("critical_event", "TestAction")
        handler, ignore = handlers[0]

        with pytest.raises(RuntimeError):
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Состояние должно остаться прежним
        assert coordinator._plugin_states[id(plugin)] == initial_state

    # ------------------------------------------------------------------
    # ТЕСТЫ: Смешанные сценарии
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_mixed_exceptions_handlers(self, event_factory):
        """
        Плагин с разными обработчиками (ignore=True и False).

        Проверяем, что флаги работают независимо для каждого обработчика.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Получаем обработчики для разных событий
        handlers_ignored = coordinator._get_handlers("test_event", "TestAction")
        handlers_critical = coordinator._get_handlers("critical_event", "TestAction")

        assert len(handlers_ignored) == 1
        assert len(handlers_critical) == 1
        assert handlers_ignored[0][1] is True  # ignore=True
        assert handlers_critical[0][1] is False  # ignore=False

    @pytest.mark.anyio
    async def test_multiple_handlers_one_fails(self, event_factory):
        """
        Если один обработчик падает с ignore=False, остальные не выполняются.

        Важно для понимания поведения при параллельном запуске.
        В текущей реализации обработчики запускаются последовательно
        через _run_single_handler, поэтому после падения следующие не запустятся.
        """

        # Создаём плагин с двумя обработчиками на одно событие
        class MixedPlugin(IgnoreExceptionsPlugin):
            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler1(self, state, event):
                self.handlers_called.append(("handler1", event.event_name))
                return state

            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler2(self, state, event):
                self.handlers_called.append(("handler2", event.event_name))
                raise ValueError("Ошибка во втором обработчике")

            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler3(self, state, event):
                self.handlers_called.append(("handler3", event.event_name))
                return state

        plugin = MixedPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="mixed_event")
        handlers = coordinator._get_handlers("mixed_event", "TestAction")

        # Запускаем обработчики по порядку
        for handler, ignore in handlers:
            try:
                await coordinator._run_single_handler(handler, ignore, plugin, event)
            except ValueError:
                break

        # Проверяем, что выполнились только обработчики до ошибки
        called = [call[0] for call in plugin.handlers_called]
        assert "handler1" in called
        assert "handler2" in called  # упал, но вызван
        assert "handler3" not in called  # не вызван

    @pytest.mark.anyio
    async def test_ignore_exceptions_with_custom_exception(self, capsys, event_factory):
        """
        Игнорируются любые типы исключений, не только стандартные.
        """

        class CustomException(Exception):
            pass

        class CustomIgnorePlugin(IgnoreExceptionsPlugin):
            @on("custom_event", ".*", ignore_exceptions=True)
            async def handle_custom(self, state, event):
                self.handlers_called.append(("custom", event.event_name))
                raise CustomException("Кастомное исключение")

        plugin = CustomIgnorePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="custom_event")
        handlers = coordinator._get_handlers("custom_event", "TestAction")
        handler, ignore = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert plugin.handlers_called == [("custom", "custom_event")]
        captured = capsys.readouterr()
        assert "ignored error: Кастомное исключение" in captured.out
