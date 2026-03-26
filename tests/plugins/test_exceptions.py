# tests/plugins/test_exceptions.py
"""
Tests for exception handling in plugins via PluginCoordinator.

Checks:
- Ignoring exceptions when ignore_exceptions=True
- Propagating exceptions when ignore_exceptions=False
- Mixed scenarios with different flags
- Logging of ignored exceptions
"""

import pytest

from action_machine.plugins.decorators import on
from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import IgnoreExceptionsPlugin


class TestPluginCoordinatorExceptions:
    """Tests for exception handling in plugins."""

    # ------------------------------------------------------------------
    # TESTS: ignore_exceptions = True
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_ignore_exceptions_true(self, capsys, event_factory):
        """
        Exception is ignored when ignore_exceptions=True.

        Verifies:
        - Handler is called
        - Exception is not propagated
        - Exception is logged to stdout
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="test_event")

        handlers = coordinator._get_handlers("test_event", "TestAction")
        assert len(handlers) == 1
        handler, ignore, _ = handlers[0]
        assert ignore is True

        # Should not raise an exception
        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Check that the handler was called
        assert plugin.handlers_called == [("ignored", "test_event")]

        # Check that the exception was logged
        captured = capsys.readouterr()
        assert "Plugin IgnoreExceptionsPlugin ignored error: This exception will be ignored" in captured.out

    @pytest.mark.anyio
    async def test_ignore_exceptions_true_state_not_updated(self, capsys, event_factory):
        """
        When an exception is ignored, the plugin state is not updated.

        The handler fails, but the new state is not saved.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Set initial state
        coordinator._plugin_states[id(plugin)] = {"counter": 42, "test": "value"}

        event = event_factory(event_name="test_event")
        handlers = coordinator._get_handlers("test_event", "TestAction")
        handler, ignore, _ = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        # State should remain unchanged (handler did not return a new state)
        assert coordinator._plugin_states[id(plugin)] == {"counter": 42, "test": "value"}

    # ------------------------------------------------------------------
    # TESTS: ignore_exceptions = False
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_ignore_exceptions_false(self, event_factory):
        """
        Exception is propagated when ignore_exceptions=False.

        Verifies:
        - Handler is called
        - Exception is propagated
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="critical_event")

        handlers = coordinator._get_handlers("critical_event", "TestAction")
        assert len(handlers) == 1
        handler, ignore, _ = handlers[0]
        assert ignore is False

        with pytest.raises(RuntimeError, match="This exception will NOT be ignored"):
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # Check that the handler was called before the error
        assert plugin.handlers_called == [("critical", "critical_event")]

    @pytest.mark.anyio
    async def test_ignore_exceptions_false_state_not_updated(self, event_factory):
        """
        When an exception is propagated, the plugin state is not updated.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Set initial state
        initial_state = {"counter": 100}
        coordinator._plugin_states[id(plugin)] = initial_state.copy()

        event = event_factory(event_name="critical_event")
        handlers = coordinator._get_handlers("critical_event", "TestAction")
        handler, ignore, _ = handlers[0]

        with pytest.raises(RuntimeError):
            await coordinator._run_single_handler(handler, ignore, plugin, event)

        # State should remain unchanged
        assert coordinator._plugin_states[id(plugin)] == initial_state

    # ------------------------------------------------------------------
    # TESTS: Mixed scenarios
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_mixed_exceptions_handlers(self, event_factory):
        """
        Plugin with different handlers (ignore=True and False).

        Verifies that flags work independently for each handler.
        """
        plugin = IgnoreExceptionsPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        # Get handlers for different events
        handlers_ignored = coordinator._get_handlers("test_event", "TestAction")
        handlers_critical = coordinator._get_handlers("critical_event", "TestAction")

        assert len(handlers_ignored) == 1
        assert len(handlers_critical) == 1
        assert handlers_ignored[0][1] is True  # ignore=True
        assert handlers_critical[0][1] is False  # ignore=False

    @pytest.mark.anyio
    async def test_multiple_handlers_one_fails(self, event_factory):
        """
        If one handler fails with ignore=False, the others are not executed.

        Important for understanding behavior in parallel execution.
        In the current implementation, handlers are executed sequentially
        via _run_single_handler, so after a failure, subsequent ones are not run.
        """

        # Create a plugin with two handlers for the same event
        class MixedPlugin(IgnoreExceptionsPlugin):
            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler1(self, state, event):
                self.handlers_called.append(("handler1", event.event_name))
                return state

            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler2(self, state, event):
                self.handlers_called.append(("handler2", event.event_name))
                raise ValueError("Error in second handler")

            @on("mixed_event", ".*", ignore_exceptions=False)
            async def handler3(self, state, event):
                self.handlers_called.append(("handler3", event.event_name))
                return state

        plugin = MixedPlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="mixed_event")
        handlers = coordinator._get_handlers("mixed_event", "TestAction")

        # Run handlers in order
        for handler, ignore, p in handlers:
            try:
                await coordinator._run_single_handler(handler, ignore, p, event)
            except ValueError:
                break

        # Check that only handlers before the error were executed
        called = [call[0] for call in plugin.handlers_called]
        assert "handler1" in called
        assert "handler2" in called  # failed, but was called
        assert "handler3" not in called  # not called

    @pytest.mark.anyio
    async def test_ignore_exceptions_with_custom_exception(self, capsys, event_factory):
        """
        Any exception type is ignored, not only standard ones.
        """

        class CustomException(Exception):
            pass

        class CustomIgnorePlugin(IgnoreExceptionsPlugin):
            @on("custom_event", ".*", ignore_exceptions=True)
            async def handle_custom(self, state, event):
                self.handlers_called.append(("custom", event.event_name))
                raise CustomException("Custom exception")

        plugin = CustomIgnorePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        event = event_factory(event_name="custom_event")
        handlers = coordinator._get_handlers("custom_event", "TestAction")
        handler, ignore, _ = handlers[0]

        await coordinator._run_single_handler(handler, ignore, plugin, event)

        assert plugin.handlers_called == [("custom", "custom_event")]
        captured = capsys.readouterr()
        assert "Plugin CustomIgnorePlugin ignored error: Custom exception" in captured.out
