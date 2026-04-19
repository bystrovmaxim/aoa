# tests/intents/plugins/test_exceptions.py
"""Tests for exception handling in plugin handlers.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Tests the behavior of the PluginRunContext in case of errors in plugin handlers.
The @on decorator takes an ignore_exceptions parameter, which specifies
error handling strategy:

- ignore_exceptions=True: handler error is suppressed; when transmitted
  log_coordinator is written CRITICAL in Channel.error. Plugin status
  NOT updated with the return value (return is not executed), but
  in-place mutations of dict made before raise remain visible because
  dict is a mutable object and is passed by reference.

- ignore_exceptions=False: the handler error is thrown out
  via emit_event(). This interrupts the action and allows
  machine to process the error at the top level.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

ignore_exceptions=True:
- The error is suppressed, emit_event() does not throw an exception.
- With log_coordinator - one critical + Channel.error entry per suppressed failure.
- In-place mutation of state before raise is visible (before_error=True).
- The code after raise is not executed (after_error remains False).

ignore_exceptions=False:
- RuntimeError is thrown from emit_event() with the correct message.
- Custom exception CustomPluginException is thrown while preserving the type."""

import pytest

from action_machine.logging.channel import Channel
from action_machine.logging.level import Level
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_result import BaseResult
from action_machine.plugin.events import GlobalFinishEvent
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from tests.intents.logging.test_log_coordinator import RecordingLogger

from .conftest import (
    _TEST_ACTION_CLASS,
    _TEST_ACTION_NAME,
    _TEST_CONTEXT,
    _TEST_PARAMS,
    CounterPlugin,
    CustomExceptionPlugin,
    CustomPluginError,
    IgnoredErrorPlugin,
    PropagatedErrorPlugin,
    emit_global_finish,
)


class TestIgnoreExceptionsTrue:
    """Behavior tests for ignore_exceptions=True - errors are suppressed."""

    @pytest.mark.anyio
    async def test_error_suppressed_no_exception(self):
        """IgnoredErrorPlugin throws RuntimeError with ignore_exceptions=True.
        emit_event() completes without throwing an exception - the error is suppressed."""
        #Arrange - plugin with a crash handler (ignore=True)
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act + Assert - there should be no exception
        await emit_global_finish(plugin_ctx)

    @pytest.mark.anyio
    async def test_in_place_mutation_before_raise_visible(self):
        """IgnoredErrorPlugin mutates state["before_error"]=True to raise.
        Since state is a dict (mutable object, passed by reference),
        An in-place mutation remains visible even when the error is suppressed."""
        #Arrange is a plugin that mutates state to raise
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act - the event is processed, the error is suppressed
        await emit_global_finish(plugin_ctx)

        #Assert - mutation to raise is visible
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["before_error"] is True

    @pytest.mark.anyio
    async def test_code_after_raise_not_executed(self):
        """IgnoredErrorPlugin: the code after raise is not executed.
        state["after_error"] remains False (initial value)."""
        #Arrange - plugin with code after raise (which will not be executed)
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act - the event is being processed
        await emit_global_finish(plugin_ctx)

        #Assert - the code after raise was not executed
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["after_error"] is False

    @pytest.mark.anyio
    async def test_suppressed_error_emits_critical_on_error_channel_parallel(self) -> None:
        """All ignore=True → gather; CRITICAL with the Channel.error mask fails."""
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        recording = RecordingLogger()
        log_coord = LogCoordinator(loggers=[recording])

        event = GlobalFinishEvent(
            action_class=_TEST_ACTION_CLASS,
            action_name=_TEST_ACTION_NAME,
            nest_level=1,
            context=_TEST_CONTEXT,
            params=_TEST_PARAMS,
            result=BaseResult(),
            duration_ms=0.0,
        )
        await plugin_ctx.emit_event(
            event,
            log_coordinator=log_coord,
            machine_name="TestMachine",
            mode="test",
        )

        assert len(recording.records) == 1
        rec = recording.records[0]
        assert rec["var"]["level"].mask == Level.critical
        assert rec["var"]["channels"].mask == Channel.error
        assert "on_error_handler" in rec["message"]
        assert "Ignored error" in rec["message"]
        assert "suppressed" in rec["message"].lower()

    @pytest.mark.anyio
    async def test_suppressed_error_emits_critical_sequential_path(self) -> None:
        """Mix ignore True/False → sequentially; a suppressed failure is logged."""
        plugin = IgnoredErrorPlugin()
        counter = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin, counter])
        plugin_ctx = await coordinator.create_run_context()
        recording = RecordingLogger()
        log_coord = LogCoordinator(loggers=[recording])

        event = GlobalFinishEvent(
            action_class=_TEST_ACTION_CLASS,
            action_name=_TEST_ACTION_NAME,
            nest_level=1,
            context=_TEST_CONTEXT,
            params=_TEST_PARAMS,
            result=BaseResult(),
            duration_ms=0.0,
        )
        await plugin_ctx.emit_event(
            event,
            log_coordinator=log_coord,
            machine_name="TestMachine",
            mode="test",
        )

        assert len(recording.records) == 1
        assert recording.records[0]["var"]["channels"].mask == Channel.error
        assert plugin_ctx.get_plugin_state(counter)["count"] == 1


class TestIgnoreExceptionsFalse:
    """Tests of behavior when ignore_exceptions=False - errors are thrown."""

    @pytest.mark.anyio
    async def test_runtime_error_propagates(self):
        """PropagatedErrorPlugin throws RuntimeError with ignore_exceptions=False.
        The error is thrown from emit_event() with the correct message."""
        #Arrange - a plugin with a critical handler
        plugin = PropagatedErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act + Assert - RuntimeError is thrown
        with pytest.raises(RuntimeError, match="Strict error must propagate"):
            await emit_global_finish(plugin_ctx)

    @pytest.mark.anyio
    async def test_custom_exception_preserves_type(self):
        """CustomExceptionPlugin throws CustomPluginException.
        The type of custom exception is saved when forwarding -
        the calling code can catch a specific type."""
        #Arrange - plugin with custom exclusion
        plugin = CustomExceptionPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        #Act + Assert - CustomPluginException is thrown with a message
        with pytest.raises(CustomPluginError, match="Custom plugin error"):
            await emit_global_finish(plugin_ctx)
            await emit_global_finish(plugin_ctx)
