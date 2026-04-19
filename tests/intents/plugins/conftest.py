# tests/intents/plugins/conftest.py
"""Test plugins and fixtures for the tests/intents/plugins/ package.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Contains test plugins, event emission helpers and fixtures,
used by all test modules in tests/intents/plugins/.

All plugins use typed subscription via event classes
from the BasePluginEvent hierarchy [1]:
    @on(GlobalFinishEvent) - instead of @on("global_finish", ".*")
    @on(GlobalStartEvent) - instead of @on("global_start", ".*")
    @on(BeforeRegularAspectEvent) - instead of @on("before:aspect_name", ".*")
    @on(AfterRegularAspectEvent) - instead of @on("after:aspect_name", ".*")
    @on(UnhandledErrorEvent) - instead of @on("on_error", ".*")

Handlers receive specific typed event objects
instead of a single PluginEvent with Optional fields.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
HELPER emit_global_finish()
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Creates a GlobalFinishEvent object with test field values and passes
in plugin_ctx.emit_event(). Used in test_emit.py, test_handlers.py,
test_exceptions.py, test_concurrency.py to emulate termination event
actions without running the full machine conveyor.

Similar helpers emit_global_start(), emit_before_regular(),
emit_after_regular() generates other event types for filtering tests.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TEST PLUGINS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

CounterPlugin
    Minimal counter plugin. One GlobalFinishEvent handler for
    all actions. Increments state["count"]. ignore_exceptions=False.

DualHandlerPlugin
    Plugin with two handlers for one event (GlobalFinishEvent).
    on_handler_a increments state["a"] by 1.
    on_handler_b increments state["b"] by 10.
    Both ignore_exceptions=False are sequential execution.

CustomInitPlugin
    Plugin with a parameterized initial state.
    Accepts an initial_value in the constructor.

RecordingPlugin
    Recorder plugin. Records event type and action_name
    in state["events"] for each GlobalFinishEvent.

SelectivePlugin
    Plugin with action_name_pattern filter. Reacts only to actions
    containing "Order" in the name.

AlphaPlugin
    Plugin with GlobalFinishEvent handler - reacts to all actions.

BetaPlugin
    Plugin with GlobalFinishEvent handler with action_name_pattern=".*Order.*".
    Reacts only to actions with "Order" in the name.

GammaPlugin
    Plugin with GlobalStartEvent handler (not GlobalFinishEvent).
    Used to check that searching for GlobalFinishEvent does not return
    handlers subscribed to GlobalStartEvent.

MultiEventPlugin
    Plugin with three handlers for different events and filters.
    on_start: GlobalStartEvent.
    on_finish: GlobalFinishEvent.
    on_order_finish: GlobalFinishEvent with action_name_pattern=".*Order.*".

IgnoredErrorPlugin
    Plugin with ignore_exceptions=True, which mutates state before raise.
    Checks the visibility of an in-place mutation when a bug is suppressed.

PropagatedErrorPlugin
    Plugin with ignore_exceptions=False, throwing RuntimeError.
    The error is propagated through emit_event().

CustomExceptionPlugin
    Plugin with ignore_exceptions=False, throwing CustomPluginError.
    Checks that the custom exception type is preserved during forwarding.

SuccessAfterFailPlugin
    Plugin with success handler. ignore_exceptions=False.
    Used to check that the exception is a critical plugin
    interrupts execution.

SlowParallelPlugin
    Plugin with 0.1s delay. ignore_exceptions=True.
    Used to check parallel execution.

SlowSequentialPlugin
    Plugin with 0.1s delay. ignore_exceptions=False.
    Used to check sequential execution."""
from __future__ import annotations

import asyncio

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.intents.plugins.events import (
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.intents.plugins.plugin_run_context import PluginRunContext
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.testing import StubTesterRole
from tests.scenarios.domain_model import PingAction

# ═════════════════════════════════════════════════════════════════════════════
#Custom exception for tests
# ═════════════════════════════════════════════════════════════════════════════

class CustomPluginError(Exception):
    """Custom exception for plugin error throwing tests."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
#Test context and parameters for helpers
# ═════════════════════════════════════════════════════════════════════════════

_TEST_CONTEXT = Context(user=UserInfo(user_id="test_user", roles=(StubTesterRole,)))
_TEST_PARAMS = BaseParams()
_TEST_ACTION_CLASS = PingAction
_TEST_ACTION_NAME = "tests.domain.ping_action.PingAction"


# ═════════════════════════════════════════════════════════════════════════════
#Event Emission Helpers
# ═════════════════════════════════════════════════════════════════════════════

async def emit_global_finish(
    plugin_ctx: PluginRunContext,
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    result: BaseResult | None = None,
    duration_ms: float = 0.0,
    nest_level: int = 1,
) -> None:
    """Creates a GlobalFinishEvent with test values ​​and emits via plugin_ctx.

    Used in test_emit.py, test_handlers.py, test_exceptions.py,
    test_concurrency.py to emulate an action completion event without
    launching a full machine conveyor.

    Arguments:
        plugin_ctx: plugin context for emission.
        action_name: The fully qualified string name of the action.
        action_class: action type.
        context: execution context (default test).
        params: input parameters (empty by default).
        result: the result of the action (empty by default).
        duration_ms: Duration in milliseconds.
        nest_level: nesting level."""
    event = GlobalFinishEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
        result=result or BaseResult(),
        duration_ms=duration_ms,
    )
    await plugin_ctx.emit_event(event)


async def emit_global_start(
    plugin_ctx: PluginRunContext,
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    nest_level: int = 1,
) -> None:
    """Creates a GlobalStartEvent with test values ​​and emits via plugin_ctx.

    Arguments:
        plugin_ctx: plugin context for emission.
        action_name: The fully qualified string name of the action.
        action_class: action type.
        context: execution context (default test).
        params: input parameters (empty by default).
        nest_level: nesting level."""
    event = GlobalStartEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
    )
    await plugin_ctx.emit_event(event)


def make_global_finish_event(
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    result: BaseResult | None = None,
    duration_ms: float = 0.0,
    nest_level: int = 1,
) -> GlobalFinishEvent:
    """Creates a GlobalFinishEvent without emission - for get_handlers() tests.

    Arguments:
        action_name: The fully qualified string name of the action.
        action_class: action type.
        context: execution context.
        params: input parameters.
        result: the result of the action.
        duration_ms: Duration in milliseconds.
        nest_level: nesting level.

    Returns:
        GlobalFinishEvent with fields filled in."""
    return GlobalFinishEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
        result=result or BaseResult(),
        duration_ms=duration_ms,
    )


def make_global_start_event(
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    nest_level: int = 1,
) -> GlobalStartEvent:
    """Creates a GlobalStartEvent without emission - for get_handlers() tests.

    Returns:
        GlobalStartEvent with fields filled in."""
    return GlobalStartEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
    )


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_handlers.py
# ═════════════════════════════════════════════════════════════════════════════

class CounterPlugin(Plugin):
    """Minimal counter plugin.

    One GlobalFinishEvent handler for all actions. Increments
    state["count"] on every call. ignore_exceptions=False —
    critical handler, an error is thrown."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_count(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["count"] += 1
        return state


class DualHandlerPlugin(Plugin):
    """Plugin with two handlers for one event (GlobalFinishEvent).

    on_handler_a increments state["a"] by 1.
    on_handler_b increments state["b"] by 10.
    Both ignore_exceptions=False are sequential execution."""

    async def get_initial_state(self) -> dict:
        return {"a": 0, "b": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_handler_a(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["a"] += 1
        return state

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_handler_b(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["b"] += 10
        return state


class CustomInitPlugin(Plugin):
    """Plugin with a parameterized initial state.

    Accepts an initial_value in the constructor. get_initial_state() returns
    {"value": initial_value}. The on_increment handler adds 1 to value."""

    def __init__(self, initial_value: int = 100):
        self._initial_value = initial_value

    async def get_initial_state(self) -> dict:
        return {"value": self._initial_value}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_increment(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["value"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_emit.py
# ═════════════════════════════════════════════════════════════════════════════

class RecordingPlugin(Plugin):
    """Recorder plugin.

    Writes the event type and action_name to state["events"]
    at each GlobalFinishEvent. Used to check
    that emit_event delivers events and the fields are correct."""

    async def get_initial_state(self) -> dict:
        return {"events": []}

    @on(GlobalFinishEvent)
    async def on_record(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["events"].append({
            "event_type": type(event).__name__,
            "action_name": event.action_name,
            "nest_level": event.nest_level,
            "duration_ms": event.duration_ms,
        })
        return state


class SelectivePlugin(Plugin):
    """Plugin with action_name_pattern filter.

    Only responds to actions containing "Order" in the full name.
    Used to check that action_name_pattern is filtering events."""

    async def get_initial_state(self) -> dict:
        return {"order_events": []}

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_event(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["order_events"].append(event.action_name)
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_find_plugin.py
# ═════════════════════════════════════════════════════════════════════════════

class AlphaPlugin(Plugin):
    """Plugin with GlobalFinishEvent handler - reacts to all actions."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent)
    async def on_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


class BetaPlugin(Plugin):
    """Plugin with GlobalFinishEvent handler with action_name_pattern=".*Order.*".

    Only responds to actions containing "Order" in the fully qualified class name."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


class GammaPlugin(Plugin):
    """Plugin with GlobalStartEvent handler (not GlobalFinishEvent).

    Used to check that searching for GlobalFinishEvent does not return
    handlers subscribed to GlobalStartEvent."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state: dict, event: GlobalStartEvent, log) -> dict:
        return state


class MultiEventPlugin(Plugin):
    """Plugin with three handlers for different events and filters.

    on_start: GlobalStartEvent for all actions.
    on_finish: GlobalFinishEvent for all actions.
    on_order_finish: GlobalFinishEvent for actions with "Order" in the name.

    For GlobalFinishEvent + "*OrderAction" there must be two handlers
    (on_finish and on_order_finish). For GlobalFinishEvent + "PingAction" -
    one(on_finish). For GlobalStartEvent + any action is one (on_start)."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state: dict, event: GlobalStartEvent, log) -> dict:
        return state

    @on(GlobalFinishEvent)
    async def on_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_exceptions.py
# ═════════════════════════════════════════════════════════════════════════════

class IgnoredErrorPlugin(Plugin):
    """Plugin with ignore_exceptions=True, which mutates state before raise.

    Mutates state["before_error"]=True, then throws RuntimeError.
    ignore_exceptions=True - the error is suppressed, but the mutation is in-place
    state is visible (state is a mutable dict, passed by reference)."""

    async def get_initial_state(self) -> dict:
        return {"before_error": False, "after_error": False}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_error_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["before_error"] = True
        raise RuntimeError("Ignored error")
        #state["after_error"] = True # will not execute


class PropagatedErrorPlugin(Plugin):
    """Plugin with ignore_exceptions=False, throwing RuntimeError.

    The error is propagated through emit_event()."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_strict_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise RuntimeError("Strict error must propagate")


class CustomExceptionPlugin(Plugin):
    """Plugin with ignore_exceptions=False, throwing CustomPluginError.

    Checks that the custom exception type is preserved during forwarding."""

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_custom_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise CustomPluginError("Custom plugin error")


class SuccessAfterFailPlugin(Plugin):
    """Plugin with success handler. ignore_exceptions=False.

    Used to check that the exception is a critical plugin
    interrupts execution (this plugin should not get control
    if the previous critical plugin has failed)."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_success_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["count"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_concurrency.py
# ═════════════════════════════════════════════════════════════════════════════

class SlowParallelPlugin(Plugin):
    """Plugin with 0.1s delay. ignore_exceptions=True.

    If there are several such plugins, PluginRunContext selects
    parallel strategy (asyncio.gather). Total time ≈ 0.1s,
    and not 0.1s × N."""

    async def get_initial_state(self) -> dict:
        return {"executed": False}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(0.1)
        state["executed"] = True
        return state


class SlowSequentialPlugin(Plugin):
    """Plugin with 0.1s delay. ignore_exceptions=False.

    If there is at least one such plugin, PluginRunContext selects
    consistent strategy. Total time ≈ 0.1s × N."""

    async def get_initial_state(self) -> dict:
        return {"executed": False}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(0.1)
        state["executed"] = True
        return state


# ═════════════════════════════════════════════════════════════════════════════
#Plugins for test_concurrency.py (parameterized delays)
# ═════════════════════════════════════════════════════════════════════════════

class SlowPluginIgnore(Plugin):
    """Plugin with parameterized delay. ignore_exceptions=True.

    If there are several such plugins, PluginRunContext selects
    parallel strategy (asyncio.gather). Total time ≈ max(delay),
    not sum(delay)."""

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPluginIgnore(Plugin):
    """Plugin without delay. ignore_exceptions=True.

    Used in conjunction with SlowPluginIgnore to check that the
    The plugin terminates along with the slow ones when executed in parallel."""

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_fast_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["calls"].append("fast")
        return state


class SlowPluginNoIgnore(Plugin):
    """Plugin with parameterized delay. ignore_exceptions=False.

    The presence of at least one such plugin switches the PluginRunContext
    to a consistent strategy. Total time ≈ sum(delay)."""

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FailingPluginIgnore(Plugin):
    """Plugin that throws RuntimeError. ignore_exceptions=True.

    The error is suppressed and the remaining plugins continue to work.
    Used to check that a crashed plugin does not interrupt
    parallel execution."""

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_failing_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise RuntimeError("Plugin intentionally failed")
        raise RuntimeError("Plugin intentionally failed")
