# tests2/plugins/test_find_plugin.py
"""
Тесты поиска обработчиков плагинов через plugin.get_handlers().

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет механизм поиска обработчиков в экземпляре Plugin. Метод
get_handlers(event_name, class_name) сканирует MRO класса плагина,
находит методы с атрибутом _on_subscriptions и для каждой подписки
проверяет совпадение event_type и action_filter (regex через re.search).

Возвращает список кортежей (handler, ignore_exceptions), где handler —
unbound-метод из cls.__dict__. Вызывающий код (PluginRunContext)
передаёт экземпляр плагина как self при вызове.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Плагин с обработчиком ".*" находит обработчик для любого действия.
- Плагин с фильтром ".*Order.*" находит обработчик только для действий
  с "Order" в имени.
- Плагин, подписанный на global_start, не находится при поиске global_finish.
- Плагин с несколькими обработчиками на разные события возвращает
  правильное количество для каждой комбинации event+action.
- Фильтр action_filter применяется через re.search (не fullmatch) —
  совпадение в любом месте строки.
- Координатор без плагинов корректно работает.
"""

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    AlphaPlugin,
    BetaPlugin,
    GammaPlugin,
    MultiEventPlugin,
)


class TestPluginGetHandlers:
    """Тесты метода Plugin.get_handlers() — поиск обработчиков по событию и действию."""

    def test_find_handler_for_any_action(self):
        """
        AlphaPlugin подписан на global_finish с фильтром ".*".
        Для любого действия должен найтись ровно один обработчик on_finish.
        """
        # Arrange — создаём плагин с обработчиком для всех действий
        plugin = AlphaPlugin()

        # Act — ищем обработчики global_finish для произвольного действия
        handlers = plugin.get_handlers("global_finish", "test.module.SomeAction")

        # Assert — найден один обработчик с правильным именем
        assert len(handlers) == 1
        handler_func, _ignore = handlers[0]
        assert handler_func.__name__ == "on_finish"

    def test_find_handler_with_order_filter(self):
        """
        BetaPlugin подписан на global_finish с фильтром ".*Order.*".
        Для CreateOrderAction должен найтись обработчик.
        Для PingAction — не должен.
        """
        # Arrange — плагин реагирует только на действия с "Order" в имени
        plugin = BetaPlugin()

        # Act + Assert — действие с "Order" в имени → обработчик найден
        order_handlers = plugin.get_handlers("global_finish", "app.actions.CreateOrderAction")
        assert len(order_handlers) == 1

        # Act + Assert — действие без "Order" → обработчик не найден
        ping_handlers = plugin.get_handlers("global_finish", "app.actions.PingAction")
        assert len(ping_handlers) == 0

    def test_two_plugins_different_filters(self):
        """
        AlphaPlugin (".*") и BetaPlugin (".*Order.*") — для CreateOrderAction
        оба находят обработчики, для PingAction — только AlphaPlugin.
        """
        # Arrange — два плагина с разными фильтрами
        alpha = AlphaPlugin()
        beta = BetaPlugin()

        # Act — ищем обработчики для CreateOrderAction
        alpha_order = alpha.get_handlers("global_finish", "test.CreateOrderAction")
        beta_order = beta.get_handlers("global_finish", "test.CreateOrderAction")

        # Assert — оба нашли обработчики для Order
        assert len(alpha_order) == 1
        assert len(beta_order) == 1

        # Act — ищем обработчики для PingAction
        alpha_ping = alpha.get_handlers("global_finish", "test.PingAction")
        beta_ping = beta.get_handlers("global_finish", "test.PingAction")

        # Assert — только Alpha нашёл (.*), Beta не нашёл (нет "Order")
        assert len(alpha_ping) == 1
        assert len(beta_ping) == 0

    def test_wrong_event_type_returns_empty(self):
        """
        GammaPlugin подписан на global_start, не на global_finish.
        Поиск для global_finish возвращает пустой список.
        """
        # Arrange — плагин подписан только на global_start
        plugin = GammaPlugin()

        # Act — ищем обработчики global_finish
        handlers = plugin.get_handlers("global_finish", "test.SomeAction")

        # Assert — обработчики не найдены (событие не совпадает)
        assert len(handlers) == 0

    def test_multi_event_plugin_global_finish_with_order(self):
        """
        MultiEventPlugin имеет три обработчика. Для global_finish +
        CreateOrderAction должны найтись два: on_finish (".*")
        и on_order_finish (".*Order.*").
        """
        # Arrange — плагин с тремя подписками на разные события
        plugin = MultiEventPlugin()

        # Act — ищем обработчики global_finish для OrderAction
        handlers = plugin.get_handlers("global_finish", "test.CreateOrderAction")

        # Assert — два обработчика: on_finish и on_order_finish
        assert len(handlers) == 2
        handler_names = {h[0].__name__ for h in handlers}
        assert handler_names == {"on_finish", "on_order_finish"}

    def test_multi_event_plugin_global_finish_without_order(self):
        """
        MultiEventPlugin: для global_finish + PingAction должен найтись
        только один обработчик on_finish (".*"), on_order_finish не совпадает.
        """
        # Arrange — тот же плагин с тремя подписками
        plugin = MultiEventPlugin()

        # Act — ищем обработчики global_finish для PingAction
        handlers = plugin.get_handlers("global_finish", "test.PingAction")

        # Assert — только on_finish (.*), on_order_finish не совпадает
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_finish"

    def test_multi_event_plugin_global_start(self):
        """
        MultiEventPlugin: для global_start должен найтись только
        один обработчик on_start.
        """
        # Arrange
        plugin = MultiEventPlugin()

        # Act — ищем обработчики global_start
        handlers = plugin.get_handlers("global_start", "test.AnyAction")

        # Assert — один обработчик on_start
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_start"

    def test_action_filter_uses_re_search(self):
        """
        action_filter применяется через re.search (не fullmatch).
        ".*Order.*" совпадает с любой строкой, содержащей "Order"
        в любой позиции.
        """
        # Arrange — плагин с фильтром ".*Order.*"
        plugin = BetaPlugin()

        # Act + Assert — "Order" в середине → совпадает
        assert len(plugin.get_handlers("global_finish", "app.actions.CreateOrderAction")) == 1

        # Act + Assert — "Order" в начале → совпадает
        assert len(plugin.get_handlers("global_finish", "OrderService.process")) == 1

        # Act + Assert — нет "Order" → не совпадает
        assert len(plugin.get_handlers("global_finish", "app.actions.UserAction")) == 0

    def test_empty_coordinator_has_no_plugins(self):
        """
        Координатор без плагинов. Плагин, существующий отдельно,
        по-прежнему находит свои обработчики через get_handlers().
        """
        # Arrange — координатор пуст, плагин существует отдельно
        coordinator = PluginCoordinator(plugins=[])
        alpha = AlphaPlugin()

        # Act + Assert — координатор пуст
        assert len(coordinator.plugins) == 0

        # Act + Assert — плагин сам по себе находит обработчики
        assert len(alpha.get_handlers("global_finish", "test.Action")) == 1
