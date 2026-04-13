# tests/intents/plugins/test_find_plugin.py
"""Tests for finding plugin handlers via plugin.get_handlers().
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Tests the mechanism for finding handlers in a Plugin instance. Method
get_handlers(event) scans the MRO of the plugin class, finds methods with
with the _on_subscriptions attribute and checks for a match for each subscription
event_class via isinstance[1].

Returns a list of tuples (handler, subscription), where handler is
unbound method from cls.__dict__, subscription - SubscriptionInfo with full
filter configuration. The calling code (PluginRunContext) checks
other filters (action_name_pattern, nest_level, etc.) via
SubscriptionInfo.matches_*() and passes the plugin instance as self
when calling [1].

Step 1 (isinstance by event_class) is done in get_handlers().
Steps 2–7 (action_class, action_name_pattern, aspect_name_pattern,
nest_level, domain, predicate) are executed in the PluginRunContext [1].

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════
- Plugin with GlobalFinishEvent handler finds a handler for any
  events of this type.
- Plugin with action_name_pattern=".*Order.*" - filtering is checked
  at the SubscriptionInfo level, not get_handlers() (step 3, not step 1).
  get_handlers() returns candidates by event_class and action_name_pattern
  checked by the calling code.
- Plugin subscribed to GlobalStartEvent is not found when searching
  by GlobalFinishEvent.
- A plugin with multiple handlers for different events returns
  the right amount for each type of event.
- The coordinator without plugins works correctly."""
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
    """Tests of the Plugin.get_handlers() method - search for handlers by event type.

    get_handlers(event) performs step 1 of the filter chain ONLY:
    isinstance(event, sub.event_class). Other filters (action_name_pattern,
    action_class, nest_level, etc.) are checked in the PluginRunContext [1]."""

    def test_find_handler_for_any_action(self):
        """AlphaPlugin is subscribed to GlobalFinishEvent without additional filters.
        For any GlobalFinishEvent there must be exactly one on_finish handler."""
        #Arrange - create a plugin with a handler for all actions
        plugin = AlphaPlugin()
        event = make_global_finish_event()

        #Act - look for handlers by event type
        handlers = plugin.get_handlers(event)

        #Assert - one handler with the correct name was found
        assert len(handlers) == 1
        handler_func, _sub = handlers[0]
        assert handler_func.__name__ == "on_finish"

    def test_beta_plugin_returns_candidate_for_any_finish_event(self):
        """BetaPlugin is subscribed to GlobalFinishEvent with action_name_pattern=".*Order.*".
        get_handlers() checks ONLY event_class (step 1) - isinstance.
        action_name_pattern is step 3, checked in PluginRunContext.

        Therefore get_handlers() returns a candidate for ANY GlobalFinishEvent,
        and filtering by action_name occurs later."""
        #Arrange - plugin with action_name_pattern (step 3, not step 1)
        plugin = BetaPlugin()
        event_order = make_global_finish_event(action_name="app.actions.CreateOrderAction")
        event_ping = make_global_finish_event(action_name="app.actions.PingAction")

        #Act - get_handlers only checks event_class
        handlers_order = plugin.get_handlers(event_order)
        handlers_ping = plugin.get_handlers(event_ping)

        #Assert - both return a candidate (step 1 passes for both)
        assert len(handlers_order) == 1
        assert len(handlers_ping) == 1

        #Assert - action_name_pattern saved in SubscriptionInfo for step 3
        _, sub = handlers_order[0]
        assert sub.action_name_pattern == ".*Order.*"

    def test_action_name_pattern_checked_via_subscription_info(self):
        """The action_name_pattern check is done via SubscriptionInfo.matches_action_name(),
        and not in get_handlers(). We demonstrate the division of responsibility."""
        # Arrange
        plugin = BetaPlugin()
        event = make_global_finish_event(action_name="app.actions.CreateOrderAction")

        #Act - get_handlers returns the candidate
        handlers = plugin.get_handlers(event)
        _, sub = handlers[0]

        #Assert - matches_action_name checks regex
        assert sub.matches_action_name("app.actions.CreateOrderAction") is True
        assert sub.matches_action_name("app.actions.PingAction") is False

    def test_two_plugins_both_match_event_class(self):
        """AlphaPlugin and BetaPlugin are both subscribed to GlobalFinishEvent.
        get_handlers() returns candidates for both - event_class matches."""
        #Arrange - two plugins with different action_name_pattern
        alpha = AlphaPlugin()
        beta = BetaPlugin()
        event = make_global_finish_event(action_name="test.CreateOrderAction")

        #Act - both find candidates by event_class
        alpha_handlers = alpha.get_handlers(event)
        beta_handlers = beta.get_handlers(event)

        #Assert - both returned one candidate each
        assert len(alpha_handlers) == 1
        assert len(beta_handlers) == 1

    def test_wrong_event_type_returns_empty(self):
        """GammaPlugin is subscribed to GlobalStartEvent, not to GlobalFinishEvent.
        Searching for GlobalFinishEvent returns an empty list - isinstance fails."""
        #Arrange - the plugin is subscribed only to GlobalStartEvent
        plugin = GammaPlugin()
        event = make_global_finish_event()

        #Act - looking for GlobalFinishEvent handlers
        handlers = plugin.get_handlers(event)

        #Assert - no handlers found (event_class does not match)
        assert len(handlers) == 0

    def test_gamma_plugin_found_for_start_event(self):
        """GammaPlugin is subscribed to GlobalStartEvent.
        Searching for GlobalStartEvent returns a handler."""
        # Arrange
        plugin = GammaPlugin()
        event = make_global_start_event()

        # Act
        handlers = plugin.get_handlers(event)

        #Assert - one on_start handler
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_start"

    def test_multi_event_plugin_global_finish(self):
        """MultiEventPlugin has three handlers:
        - on_start: GlobalStartEvent
        - on_finish: GlobalFinishEvent
        - on_order_finish: GlobalFinishEvent (with action_name_pattern)

        For GlobalFinishEvent get_handlers() returns TWO candidates:
        on_finish and on_order_finish (both subscribed to GlobalFinishEvent).
        action_name_pattern is checked later in the PluginRunContext."""
        #Arrange - a plugin with three subscriptions for different events
        plugin = MultiEventPlugin()
        event = make_global_finish_event(action_name="test.CreateOrderAction")

        #Act - looking for GlobalFinishEvent handlers
        handlers = plugin.get_handlers(event)

        #Assert - two handlers: on_finish and on_order_finish
        assert len(handlers) == 2
        handler_names = {h[0].__name__ for h in handlers}
        assert handler_names == {"on_finish", "on_order_finish"}

    def test_multi_event_plugin_global_start(self):
        """MultiEventPlugin: for GlobalStartEvent there should be only
        one on_start handler."""
        # Arrange
        plugin = MultiEventPlugin()
        event = make_global_start_event()

        #Act - looking for GlobalStartEvent handlers
        handlers = plugin.get_handlers(event)

        #Assert - one on_start handler
        assert len(handlers) == 1
        assert handlers[0][0].__name__ == "on_start"

    def test_handler_returns_subscription_info(self):
        """get_handlers() returns tuples (handler, SubscriptionInfo).
        SubscriptionInfo contains event_class, method_name, action_name_pattern,
        ignore_exceptions and other filters."""
        # Arrange
        plugin = BetaPlugin()
        event = make_global_finish_event()

        # Act
        handlers = plugin.get_handlers(event)
        _handler_func, sub = handlers[0]

        #Assert — SubscriptionInfo contains correct data
        from action_machine.intents.plugins.events import GlobalFinishEvent
        from action_machine.intents.plugins.subscription_info import SubscriptionInfo

        assert isinstance(sub, SubscriptionInfo)
        assert sub.event_class is GlobalFinishEvent
        assert sub.method_name == "on_order_finish"
        assert sub.action_name_pattern == ".*Order.*"
        assert sub.ignore_exceptions is True  # default

    def test_empty_coordinator_has_no_plugins(self):
        """Coordinator without plugins. A plugin that exists separately
        still finds its handlers via get_handlers()."""
        #Arrange - the coordinator is empty, the plugin exists separately
        coordinator = PluginCoordinator(plugins=[])
        alpha = AlphaPlugin()
        event = make_global_finish_event()

        #Act + Assert - coordinator is empty
        assert len(coordinator.plugins) == 0

        #Act + Assert - the plugin finds handlers on its own
        assert len(alpha.get_handlers(event)) == 1
        assert len(alpha.get_handlers(event)) == 1
