# tests/plugins/test_find_plugin.py
"""
Тесты поиска обработчиков плагинов через plugin.get_handlers().
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет механизм поиска обработчиков в экземпляре Plugin. Метод
get_handlers(event) сканирует MRO класса плагина, находит методы с
атрибутом _on_subscriptions и для каждой подписки проверяет совпадение
event_class через isinstance [1].

Возвращает список кортежей (handler, subscription), где handler —
unbound-метод из cls.__dict__, subscription — SubscriptionInfo с полной
конфигурацией фильтров. Вызывающий код (PluginRunContext) проверяет
остальные фильтры (action_name_pattern, nest_level и т.д.) через
SubscriptionInfo.matches_*() и передаёт экземпляр плагина как self
при вызове [1].

Шаг 1 (isinstance по event_class) выполняется в get_handlers().
Шаги 2–7 (action_class, action_name_pattern, aspect_name_pattern,
nest_level, domain, predicate) выполняются в PluginRunContext [1].

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════
- Плагин с обработчиком GlobalFinishEvent находит обработчик для любого
  события этого типа.
- Плагин с action_name_pattern=".*Order.*" — фильтрация проверяется
  на уровне SubscriptionInfo, а не get_handlers() (шаг 3, не шаг 1).
  get_handlers() возвращает кандидатов по event_class, а action_name_pattern
  проверяется вызывающим кодом.
- Плагин, подписанный на GlobalStartEvent, не находится при поиске
  по GlobalFinishEvent.
- Плагин с несколькими обработчиками на разные события возвращает
  правильное количество для каждого типа события.
- Координатор без плагинов корректно работает.
"""
from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    AlphaPlugin,
    BetaPlugin,
    GammaPlugin,
    MultiEventPlugin,
    make_global_finish_event,
    make_global_start_event,
)


class TestPluginGetHandlers:
    """
    Тесты метода Plugin.get_handlers() — поиск обработчиков по типу события.

    get_handlers(event) выполняет ТОЛЬКО шаг 1 цепочки фильтров:
    isinstance(event, sub.event_class). Остальные фильтры (action_name_pattern,
    action_class, nest_level и т.д.) проверяются в PluginRunContext [1].
    """

    def test_find_handler_for_any_action(self):
        """
        AlphaPlugin подписан на GlobalFinishEvent без дополнительных фильтров.
        Для любого GlobalFinishEvent должен найтись ровно один обработчик on_finish.
        """
        # Arrange — создаём плагин с обработчиком для всех действий
        plugin = AlphaPlugin()
        event = make_global_finish_event()

        # Act — ищем обработчики по типу события
        handlers = plugin.get_handlers(event)

        # Assert — найден один обработчик с правильным именем
        assert len(handlers) == 1
        handler_func, _sub = handlers[0]
        assert handler_func.__name__ == "on_finish"

    def test_beta_plugin_returns_candidate_for_any_finish_event(self):
        """
        BetaPlugin подписан на GlobalFinishEvent с action_name_pattern=".*Order.*".
        get_handlers() проверяет ТОЛЬКО event_class (шаг 1) — isinstance.
        action_name_pattern — это шаг 3, проверяемый в PluginRunContext.

        Поэтому get_handlers() возвращает кандидата для ЛЮБОГО GlobalFinishEvent,
        а фильтрация по action_name происходит позже.
        """
        # Arrange — плагин с action_name_pattern (шаг 3, не шаг 1)
        plugin = BetaPlugin()
        event_order = make_global_finish_event(action_name="app.actions.CreateOrderAction")
        event_ping = make_global_finish_event(action_name="app.actions.PingAction")

        # Act — get_handlers проверяет только event_class
        handlers_order = plugin.get_handlers(event_order)
        handlers_ping = plugin.get_handlers(event_ping)

        # Assert — оба возвращают кандидата (шаг 1 проходит для обоих)
        assert len(handlers_order) == 1
        assert len(handlers_ping) == 1

        # Assert — action_name_pattern сохранён в SubscriptionInfo для шага 3
        _, sub = handlers_order[0]
        assert sub.action_name_pattern == ".*Order.*"

    def test_action_name_pattern_checked_via_subscription_info(self):
        """
        Проверка action_name_pattern выполняется через SubscriptionInfo.matches_action_name(),
        а не в get_handlers(). Демонстрируем разделение ответственности.
        """
        # Arrange
        plugin = BetaPlugin()
        event = make_global_finish_event(action_name="app.actions.CreateOrderAction")

        # Act — get_handlers возвращает кандидата
        handlers = plugin.get_handlers(event)
        _, sub = handlers[0]

        # Assert — matches_action_name проверяет regex
        assert sub.matches_action_name("app.actions.CreateOrderAction") is True
        assert sub.matches_action_name("app.actions.PingAction") is False

    def test_two_plugins_both_match_event_class(self):
        """
        AlphaPlugin и BetaPlugin оба подписаны на GlobalFinishEvent.
        get_handlers() возвращает кандидатов для обоих — event_class совпадает.
        """
        # Arrange — два плагина с разными action_name_pattern
        alpha = AlphaPlugin()
        beta = BetaPlugin()
        event = make_global_finish_event(action_name="test.CreateOrderAction")

        # Act — оба находят кандидатов по event_class
        alpha_handlers = alpha.get_handlers(event)
        beta_handlers = beta.get_handlers(event)

        # Assert — оба вернули по одному кандидату
        assert len(alpha_handlers) == 1
        assert len(beta_handlers) == 1

    def test_wrong_event_type_returns_empty(self):
        """
        GammaPlugin подписан на GlobalStartEvent, не на GlobalFinishEvent.
        Поиск по GlobalFinishEvent возвращает пустой список — isinstance не проходит.
        """
        # Arrange — плагин подписан только на GlobalStartEvent
        plugin = GammaPlugin()
        event = make_global_finish_event()

        # Act — ищем обработчики GlobalFinishEvent
        handlers = plugin.get_handlers(event)

        # Assert — обработчики не найдены (event_class не совпадает)
        assert len(handlers) == 0

    def test_gamma_plugin_found_for_start_event(self):
        """
        GammaPlugin подписан на GlobalStartEvent.
        Поиск по GlobalStartEvent возвращает обработчик.
        """
        # Arrange
        plugin = GammaPlugin()
        event = make_global_start_event()

        # Act
        handlers = plugin.get_handlers(event)

        # Assert — один обработчик on_start
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_start"

    def test_multi_event_plugin_global_finish(self):
        """
        MultiEventPlugin имеет три обработчика:
        - on_start: GlobalStartEvent
        - on_finish: GlobalFinishEvent
        - on_order_finish: GlobalFinishEvent (с action_name_pattern)

        Для GlobalFinishEvent get_handlers() возвращает ДВА кандидата:
        on_finish и on_order_finish (оба подписаны на GlobalFinishEvent).
        action_name_pattern проверяется позже в PluginRunContext.
        """
        # Arrange — плагин с тремя подписками на разные события
        plugin = MultiEventPlugin()
        event = make_global_finish_event(action_name="test.CreateOrderAction")

        # Act — ищем обработчики GlobalFinishEvent
        handlers = plugin.get_handlers(event)

        # Assert — два обработчика: on_finish и on_order_finish
        assert len(handlers) == 2
        handler_names = {h[0].__name__ for h in handlers}
        assert handler_names == {"on_finish", "on_order_finish"}

    def test_multi_event_plugin_global_start(self):
        """
        MultiEventPlugin: для GlobalStartEvent должен найтись только
        один обработчик on_start.
        """
        # Arrange
        plugin = MultiEventPlugin()
        event = make_global_start_event()

        # Act — ищем обработчики GlobalStartEvent
        handlers = plugin.get_handlers(event)

        # Assert — один обработчик on_start
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_start"

    def test_handler_returns_subscription_info(self):
        """
        get_handlers() возвращает кортежи (handler, SubscriptionInfo).
        SubscriptionInfo содержит event_class, method_name, action_name_pattern,
        ignore_exceptions и другие фильтры.
        """
        # Arrange
        plugin = BetaPlugin()
        event = make_global_finish_event()

        # Act
        handlers = plugin.get_handlers(event)
        _handler_func, sub = handlers[0]

        # Assert — SubscriptionInfo содержит корректные данные
        from action_machine.intents.plugins.events import GlobalFinishEvent
        from action_machine.intents.plugins.subscription_info import SubscriptionInfo

        assert isinstance(sub, SubscriptionInfo)
        assert sub.event_class is GlobalFinishEvent
        assert sub.method_name == "on_order_finish"
        assert sub.action_name_pattern == ".*Order.*"
        assert sub.ignore_exceptions is True  # default

    def test_empty_coordinator_has_no_plugins(self):
        """
        Координатор без плагинов. Плагин, существующий отдельно,
        по-прежнему находит свои обработчики через get_handlers().
        """
        # Arrange — координатор пуст, плагин существует отдельно
        coordinator = PluginCoordinator(plugins=[])
        alpha = AlphaPlugin()
        event = make_global_finish_event()

        # Act + Assert — координатор пуст
        assert len(coordinator.plugins) == 0

        # Act + Assert — плагин сам по себе находит обработчики
        assert len(alpha.get_handlers(event)) == 1
