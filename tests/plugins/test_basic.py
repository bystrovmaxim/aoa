"""
Тесты базовых операций PluginCoordinator.

Проверяем:
- Инициализацию с разными параметрами
- Получение обработчиков (get_handlers)
- Кеширование обработчиков
- Фильтрацию по классам и событиям
"""

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import ClassFilterPlugin, MultiHandlerPlugin, SimplePlugin


class TestPluginCoordinatorBasic:
    """Базовые тесты координатора плагинов."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Инициализация
    # ------------------------------------------------------------------

    def test_init_with_plugins(self):
        """Инициализация со списком плагинов."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        assert coordinator._plugins == [plugin]
        assert coordinator._max_concurrent_handlers == 10
        assert coordinator._handler_cache == {}
        assert coordinator._plugin_states == {}

    def test_init_with_custom_max_concurrent(self):
        """Инициализация с кастомным max_concurrent_handlers."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin], max_concurrent_handlers=5)

        assert coordinator._max_concurrent_handlers == 5

    def test_init_empty_plugins(self):
        """Инициализация с пустым списком плагинов."""
        coordinator = PluginCoordinator([])

        assert coordinator._plugins == []
        assert coordinator._handler_cache == {}

    # ------------------------------------------------------------------
    # ТЕСТЫ: get_handlers — простые случаи
    # ------------------------------------------------------------------

    def test_get_handlers_simple(self):
        """Получение обработчиков для простого плагина."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        handlers = coordinator._get_handlers("test_event", "any.action.Name")

        assert len(handlers) == 1
        handler, ignore = handlers[0]
        assert handler.__name__ == "handle_test"
        assert ignore is False

    def test_get_handlers_multiple_plugins(self):
        """
        Обработчики из нескольких плагинов объединяются.

        SimplePlugin подписан только на "test_event" (fullmatch).
        MultiHandlerPlugin подписан на "event1", "event2", "event.*".

        При запросе "event1":
        - SimplePlugin: handle_test подписан на "test_event" →
          fullmatch("test_event", "event1") = False → 0 обработчиков
        - MultiHandlerPlugin: handle_event1 ("event1" → совпадает)
          и handle_any_event ("event.*" → совпадает) → 2 обработчика

        Итого: 2 обработчика.
        """
        plugin1 = SimplePlugin()
        plugin2 = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        handlers = coordinator._get_handlers("event1", "any.action.Name")

        assert len(handlers) == 2
        handler_names = [h[0].__name__ for h in handlers]
        assert "handle_event1" in handler_names
        assert "handle_any_event" in handler_names
        assert "handle_test" not in handler_names

    def test_get_handlers_multiple_plugins_test_event(self):
        """
        При запросе "test_event":
        - SimplePlugin: handle_test совпадает → 1 обработчик
        - MultiHandlerPlugin: ни один не совпадает → 0 обработчиков

        Итого: 1 обработчик.
        """
        plugin1 = SimplePlugin()
        plugin2 = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        handlers = coordinator._get_handlers("test_event", "any.action.Name")

        assert len(handlers) == 1
        handler_names = [h[0].__name__ for h in handlers]
        assert "handle_test" in handler_names

    def test_get_handlers_caching(self):
        """Результат get_handlers кешируется."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Первый вызов
        handlers1 = coordinator._get_handlers("test_event", "any.action")

        # Второй вызов с теми же параметрами
        handlers2 = coordinator._get_handlers("test_event", "any.action")

        assert handlers1 is handlers2  # один и тот же объект (кеш)
        assert len(coordinator._handler_cache) == 1
        assert ("test_event", "any.action") in coordinator._handler_cache

    def test_get_handlers_no_match(self):
        """Нет подходящих обработчиков -> пустой список."""
        plugin = SimplePlugin()  # только test_event
        coordinator = PluginCoordinator([plugin])

        handlers = coordinator._get_handlers("nonexistent_event", "any.action")

        assert handlers == []

    # ------------------------------------------------------------------
    # ТЕСТЫ: get_handlers — фильтрация по классам и событиям
    # ------------------------------------------------------------------

    def test_get_handlers_class_filtering(self):
        """Фильтрация по классу действия работает."""
        plugin = ClassFilterPlugin()
        coordinator = PluginCoordinator([plugin])

        # Должен подойти под .*OrderAction
        handlers_order = coordinator._get_handlers("any_event", "app.OrderAction")
        assert len(handlers_order) == 1
        assert handlers_order[0][0].__name__ == "handle_order"

        # Должен подойти под .*PaymentAction
        handlers_payment = coordinator._get_handlers("any_event", "app.PaymentAction")
        assert len(handlers_payment) == 1
        assert handlers_payment[0][0].__name__ == "handle_payment"

        # Не должен подойти ни под один
        handlers_other = coordinator._get_handlers("any_event", "app.UserAction")
        assert handlers_other == []

    def test_get_handlers_regex_event(self):
        """Регулярные выражения для событий работают."""
        plugin = MultiHandlerPlugin()  # есть event.*
        coordinator = PluginCoordinator([plugin])

        # Должен подойти под event.*
        handlers = coordinator._get_handlers("event_anything", "any.action")
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "handle_any_event"

    def test_get_handlers_multiple_matches_same_plugin(self):
        """
        Один плагин может вернуть несколько обработчиков для одного события.

        MultiHandlerPlugin должен вернуть 2 обработчика для event1:
        - handle_event1 (точное совпадение)
        - handle_any_event (regex event.*)
        """
        plugin = MultiHandlerPlugin()
        coordinator = PluginCoordinator([plugin])

        handlers = coordinator._get_handlers("event1", "any.action")

        assert len(handlers) == 2
        handler_names = [h[0].__name__ for h in handlers]
        assert "handle_event1" in handler_names
        assert "handle_any_event" in handler_names
