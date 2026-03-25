# tests/plugins/conftest.py
"""
Fixtures and test plugins for testing PluginCoordinator.
All test plugins are placed here for reuse.
"""

import asyncio
from unittest.mock import Mock

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult

# Импорт DependencyFactory исправлен: из action_machine.dependencies.dependency_factory
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.Plugins.Decorators import on
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent

# ======================================================================
# TEST PLUGINS
# ======================================================================


class PluginTestBase(Plugin):
    """
    Base test plugin.

    Provides:
    - Plugin name for identification
    - Call counter in state
    - List of called handlers for verification
    """

    def __init__(self, name="test"):
        self.name = name
        self.initial_state = {"counter": 0}
        self.handlers_called = []

    async def get_initial_state(self):
        """Returns a copy of the initial state (async)."""
        return self.initial_state.copy()


class SimplePlugin(PluginTestBase):
    """
    Plugin with a single handler for testing basic scenarios.

    Subscribed to:
    - test_event (any action class)
    """

    @on("test_event", ".*", ignore_exceptions=False)
    async def handle_test(self, state, event):
        """Simple handler that increments the counter."""
        self.handlers_called.append(("handle_test", event.event_name))
        state["counter"] = state.get("counter", 0) + 1
        return state


class MultiHandlerPlugin(PluginTestBase):
    """
    Plugin with multiple handlers for testing filtering.

    Subscribed to:
    - event1 (any class)
    - event2 (any class)
    - event.* (any class) – regular expression
    """

    @on("event1", ".*", ignore_exceptions=False)
    async def handle_event1(self, state, event):
        """Handler for event1."""
        self.handlers_called.append(("event1", event.event_name))
        state["last"] = "event1"
        return state

    @on("event2", ".*", ignore_exceptions=False)
    async def handle_event2(self, state, event):
        """Handler for event2."""
        self.handlers_called.append(("event2", event.event_name))
        state["last"] = "event2"
        return state

    @on("event.*", ".*", ignore_exceptions=False)
    async def handle_any_event(self, state, event):
        """
        Handler for any event starting with 'event'.
        Uses a regular expression.
        """
        self.handlers_called.append(("any", event.event_name))
        state["any"] = True
        return state


class ClassFilterPlugin(PluginTestBase):
    """
    Plugin with filtering by action class.

    Subscribed to:
    - any events for classes ending with OrderAction
    - any events for classes ending with PaymentAction
    """

    @on(".*", ".*OrderAction", ignore_exceptions=False)
    async def handle_order(self, state, event):
        """Handler for order-related actions."""
        self.handlers_called.append(("order", event.action_name))
        state["order"] = True
        return state

    @on(".*", ".*PaymentAction", ignore_exceptions=False)
    async def handle_payment(self, state, event):
        """Handler for payment-related actions."""
        self.handlers_called.append(("payment", event.action_name))
        state["payment"] = True
        return state


class IgnoreExceptionsPlugin(PluginTestBase):
    """
    Plugin for testing ignore_exceptions.

    Subscribed to:
    - test_event with ignore_exceptions=True
    - critical_event with ignore_exceptions=False
    """

    @on("test_event", ".*", ignore_exceptions=True)
    async def handle_ignored(self, state, event):
        """Handler that always fails, but the exception is ignored."""
        self.handlers_called.append(("ignored", event.event_name))
        raise ValueError("This exception will be ignored")

    @on("critical_event", ".*", ignore_exceptions=False)
    async def handle_critical(self, state, event):
        """Handler that fails, and the exception is propagated."""
        self.handlers_called.append(("critical", event.event_name))
        raise RuntimeError("This exception will NOT be ignored")


class SlowPlugin(PluginTestBase):
    """
    Plugin with a slow handler for concurrency tests.

    Subscribed to slow_event.
    The handler sleeps for 0.1 seconds before returning.
    """

    @on("slow_event", ".*", ignore_exceptions=False)
    async def handle_slow(self, state, event):
        """Slow handler with a delay."""
        self.handlers_called.append(("slow", event.event_name))
        await asyncio.sleep(0.1)  # 100ms delay
        state["slow_done"] = True
        return state


class CustomStatePlugin(PluginTestBase):
    """
    Plugin with custom initial state.

    Returns a state with a list and a numeric value.
    """

    async def get_initial_state(self):
        """Returns a complex initial state."""
        return {"value": 100, "items": [1, 2, 3]}


# ======================================================================
# HELPER CLASSES FOR TESTS
# ======================================================================


class MockAction(BaseAction):
    """Mock action for tests with a fixed class name."""

    _full_class_name = "test_plugin.MockAction"

    @summary_aspect("mock")
    async def summary(self, params, state, deps, connections, log):
        return MockResult()


class MockParams(BaseParams):
    """Mock action parameters."""

    pass


class MockResult(BaseResult):
    """Mock action result."""

    pass


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def simple_plugin():
    """Fixture returning a new SimplePlugin instance."""
    return SimplePlugin()


@pytest.fixture
def multi_handler_plugin():
    """Fixture returning a new MultiHandlerPlugin instance."""
    return MultiHandlerPlugin()


@pytest.fixture
def class_filter_plugin():
    """Fixture returning a new ClassFilterPlugin instance."""
    return ClassFilterPlugin()


@pytest.fixture
def ignore_exceptions_plugin():
    """Fixture returning a new IgnoreExceptionsPlugin instance."""
    return IgnoreExceptionsPlugin()


@pytest.fixture
def slow_plugin():
    """Fixture returning a new SlowPlugin instance."""
    return SlowPlugin()


@pytest.fixture
def mock_action():
    """Fixture returning a new MockAction instance."""
    return MockAction()


@pytest.fixture
def mock_params():
    """Fixture returning a new MockParams instance."""
    return MockParams()


@pytest.fixture
def mock_factory():
    """Fixture returning a mock DependencyFactory."""
    return Mock(spec=DependencyFactory)


@pytest.fixture
def mock_context():
    """Fixture returning a mock Context."""
    return Mock(spec=Context)


@pytest.fixture
def event_factory():
    """
    Factory for creating PluginEvent with default values.

    Allows tests to create events by overriding only the needed fields.
    """

    def _create_event(**kwargs):
        default_event = PluginEvent(
            event_name="test_event",
            action_name="TestAction",
            params=MockParams(),
            state_aspect={},
            is_summary=False,
            deps=Mock(spec=DependencyFactory),
            context=Mock(spec=Context),
            result=None,
            duration=None,
            nest_level=0,
        )
        # Update default values with provided kwargs
        for key, value in kwargs.items():
            setattr(default_event, key, value)
        return default_event

    return _create_event