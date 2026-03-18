# tests/plugins/test_find_plugin.py
"""
Тесты метода _find_plugin_for_handler в PluginCoordinator.

Проверяем:
- Поиск плагина по обработчику
- Ситуации, когда обработчик не принадлежит ни одному плагину
- Поиск среди нескольких плагинов
"""

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import MultiHandlerPlugin, SimplePlugin


class TestPluginCoordinatorFindPlugin:
    """Тесты поиска плагина по обработчику."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Базовый поиск
    # ------------------------------------------------------------------

    def test_find_plugin_for_handler(self):
        """Поиск плагина, которому принадлежит обработчик."""
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        # Получаем обработчик от первого плагина
        handlers1 = coordinator._get_handlers("test_event", "any")
        handler1, _ = handlers1[0]

        # Должен найти plugin1
        found = coordinator._find_plugin_for_handler(handler1)
        assert found is plugin1
        assert found is not plugin2

    def test_find_plugin_for_handler_with_multiple_plugins(self):
        """Поиск среди нескольких плагинов с разными обработчиками."""
        plugin1 = SimplePlugin()
        plugin2 = MultiHandlerPlugin()
        plugin3 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2, plugin3])

        handlers = coordinator._get_handlers("event1", "any")

        # Должен найти правильный плагин для каждого обработчика
        for handler, _ in handlers:
            found = coordinator._find_plugin_for_handler(handler)
            # Обработчики из plugin2 должны найти plugin2
            if handler.__name__ in ["handle_event1", "handle_any_event"]:
                assert found is plugin2
            else:
                assert found in [plugin1, plugin3]

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обработчик не найден
    # ------------------------------------------------------------------

    def test_find_plugin_for_handler_not_found(self):
        """Обработчик не принадлежит ни одному плагину."""
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Какой-то левый обработчик, не из плагинов
        async def fake_handler(state, event):
            pass

        found = coordinator._find_plugin_for_handler(fake_handler)
        assert found is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    def test_find_plugin_for_handler_with_unbound_method(self):
        """
        Поиск для несвязанного метода (не привязанного к экземпляру).

        Такие методы не должны находиться, так как у них нет __self__.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Берем класс, а не экземпляр
        unbound_handler = SimplePlugin.handle_test

        found = coordinator._find_plugin_for_handler(unbound_handler)
        assert found is None

    def test_find_plugin_for_handler_after_plugin_removed(self):
        """
        Если плагин был удален из списка, но обработчик остался в кеше,
        поиск должен вернуть None.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        handlers = coordinator._get_handlers("test_event", "any")
        handler, _ = handlers[0]

        # "Удаляем" плагин (в реальности так не делаем, но для теста)
        coordinator._plugins = []

        found = coordinator._find_plugin_for_handler(handler)
        assert found is None