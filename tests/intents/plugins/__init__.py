# tests/intents/plugins/__init__.py
"""
Tests for the ActionMachine plugin system.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Tests the plugin mechanism for extending ActionMachine via lifecycle event subscriptions.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

Plugin
    Abstract plugin base. Handlers are declared with @on. get_handlers(event_name,
    class_name) returns (handler, ignore_exceptions) tuples. get_initial_state() returns
    per-request initial plugin state.

PluginCoordinator
    Stateless plugin coordinator. Holds a list of Plugin instances and creates an
    isolated PluginRunContext per machine.run() via create_run_context(). No mutable
    cross-request state.

PluginRunContext
    Isolated plugin execution context for one machine.run(). Stores per-request plugin
    states in {id(plugin): state}. emit_event() dispatches to subscribed handlers.
    Execution is parallel (asyncio.gather) when all ignore_exceptions are True,
    otherwise sequential. get_plugin_state() exposes state for tests.

PluginEvent
    Frozen dataclass for events passed to handlers: event_name, action_name, params,
    state_aspect, is_summary, deps, context, result, duration, nest_level.

@on(event_type, action_filter, ignore_exceptions)
    Plugin method decorator declaring a subscription. event_type is a string such as
    "global_finish" or "before:validate". action_filter is a regex on the full action name.
    ignore_exceptions suppresses handler errors when True. Handler signature must be
    (self, state, event, log).

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/intents/plugins/
    ├── __init__.py                — this file
    ├── conftest.py                — test plugins and fixtures
    ├── test_find_plugin.py        — handler lookup, action_filter regex
    ├── test_handlers.py           — handler execution, plugin state
    ├── test_emit.py               — event dispatch, empty handlers
    ├── test_exceptions.py         — ignore_exceptions True/False, custom errors
    └── test_concurrency.py        — parallel vs sequential execution
"""
