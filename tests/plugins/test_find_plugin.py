# tests/plugins/test_find_plugin.py
"""
Тесты поиска обработчиков и плагинов.

Проверяется:
- Поиск обработчиков через plugin.get_handlers() для конкретного
  события и действия.
- Множественные плагины с разными подписками.
- Отсутствие обработчиков для несовпадающего события.
- Фильтрация по action_filter (регулярное выражение).

В новой архитектуре поиск обработчиков выполняется через
plugin.get_handlers() напрямую, без кеширования в координаторе.
PluginCoordinator — stateless, метод _find_plugin_for_handler удалён.
"""


from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_event import PluginEvent

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class AlphaPlugin(Plugin):
    """Плагин с обработчиком global_finish для всех действий."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent) -> dict:
        return state


class BetaPlugin(Plugin):
    """Плагин с обработчиком global_finish для действий *Order*."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*Order.*")
    async def on_order_finish(self, state: dict, event: PluginEvent) -> dict:
        return state


class GammaPlugin(Plugin):
    """Плагин с обработчиком global_start (не global_finish)."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent) -> dict:
        return state


class MultiHandlerPlugin(Plugin):
    """Плагин с несколькими обработчиками на разные события."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent) -> dict:
        return state

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent) -> dict:
        return state

    @on("global_finish", ".*Order.*")
    async def on_order_finish(self, state: dict, event: PluginEvent) -> dict:
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorFindPlugin:
    """Тесты поиска обработчиков через plugin.get_handlers()."""

    def test_find_plugin_for_handler(self):
        """
        AlphaPlugin имеет обработчик global_finish для ".*" —
        должен найтись для любого действия.
        """
        plugin = AlphaPlugin()
        handlers = plugin.get_handlers("global_finish", "test.SomeAction")
        assert len(handlers) == 1
        handler_func, ignore = handlers[0]
        assert handler_func.__name__ == "on_finish"

    def test_find_plugin_for_handler_with_multiple_plugins(self):
        """
        Несколько плагинов: AlphaPlugin (.*) и BetaPlugin (.*Order.*).
        Для действия CreateOrderAction оба должны найти обработчики.
        Для действия PingAction — только AlphaPlugin.
        """
        alpha = AlphaPlugin()
        beta = BetaPlugin()

        # CreateOrderAction — совпадает с обоими
        alpha_handlers = alpha.get_handlers("global_finish", "test.CreateOrderAction")
        beta_handlers = beta.get_handlers("global_finish", "test.CreateOrderAction")
        assert len(alpha_handlers) == 1
        assert len(beta_handlers) == 1

        # PingAction — совпадает только с AlphaPlugin
        alpha_handlers2 = alpha.get_handlers("global_finish", "test.PingAction")
        beta_handlers2 = beta.get_handlers("global_finish", "test.PingAction")
        assert len(alpha_handlers2) == 1
        assert len(beta_handlers2) == 0

    def test_find_plugin_for_handler_not_found(self):
        """
        GammaPlugin подписан на global_start, не на global_finish.
        Поиск для global_finish должен вернуть пустой список.
        """
        plugin = GammaPlugin()
        handlers = plugin.get_handlers("global_finish", "test.SomeAction")
        assert len(handlers) == 0

    def test_find_plugin_for_handler_with_unbound_method(self):
        """
        MultiHandlerPlugin имеет несколько обработчиков.
        Для global_finish + CreateOrderAction должны найтись два обработчика:
        on_finish (.*) и on_order_finish (.*Order.*).
        """
        plugin = MultiHandlerPlugin()
        handlers = plugin.get_handlers("global_finish", "test.CreateOrderAction")
        assert len(handlers) == 2
        handler_names = {h[0].__name__ for h in handlers}
        assert handler_names == {"on_finish", "on_order_finish"}

    def test_find_plugin_for_handler_after_plugin_removed(self):
        """
        Координатор без плагинов не содержит обработчиков.
        Плагин, существующий отдельно, по-прежнему находит свои обработчики.
        """
        alpha = AlphaPlugin()
        coordinator_without = PluginCoordinator(plugins=[])

        # Плагин сам по себе находит обработчики
        assert len(alpha.get_handlers("global_finish", "test.Action")) == 1

        # Координатор без плагинов — пуст
        assert len(coordinator_without.plugins) == 0

    def test_action_filter_regex_matching(self):
        """Фильтр action_filter применяется как regex через re.search."""
        beta = BetaPlugin()

        # Совпадает: содержит "Order"
        assert len(beta.get_handlers("global_finish", "app.actions.CreateOrderAction")) == 1
        assert len(beta.get_handlers("global_finish", "OrderService.process")) == 1

        # Не совпадает: нет "Order"
        assert len(beta.get_handlers("global_finish", "app.actions.PingAction")) == 0
        assert len(beta.get_handlers("global_finish", "app.actions.UserAction")) == 0
