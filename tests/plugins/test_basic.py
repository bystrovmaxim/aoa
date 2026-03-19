"""
Concurrency tests for plugin handlers in PluginCoordinator.

Previously, these tests verified that a semaphore limits the number of
concurrently executing handlers. Now that the semaphore has been removed
(all handlers run concurrently without restrictions), these tests are no
longer relevant and have been removed or replaced.

We keep only basic tests that ensure handlers are called correctly.
"""

import asyncio

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import MockParams, SlowPlugin


class TestPluginCoordinatorConcurrency:
    """
    Tests related to concurrent execution of plugin handlers.

    Since concurrency is now unlimited, we only verify that all handlers
    are invoked and that the total execution time is roughly the time of
    the slowest handler (they run in parallel).
    """

    @pytest.mark.anyio
    async def test_all_handlers_run_concurrently(self, mock_action, mock_factory, mock_context):
        """
        All handlers should run concurrently; total time ≈ max(handler time).
        With 5 slow handlers each taking 0.1s, total time should be ~0.1s,
        not 0.5s.
        """
        plugins = [SlowPlugin() for _ in range(5)]
        coordinator = PluginCoordinator(plugins)

        params = MockParams()

        start_time = asyncio.get_event_loop().time()

        await coordinator.emit_event(
            event_name="slow_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # All handlers run concurrently, so duration should be just over 0.1s.
        # Allow some margin for overhead.
        assert duration < 0.2, f"Expected duration < 0.2s, got {duration:.2f}s"

        for plugin in plugins:
            assert plugin.handlers_called == [("slow", "slow_event")]

    @pytest.mark.anyio
    async def test_mixed_handlers_run_concurrently(self, mock_action, mock_factory, mock_context):
        """
        Mixed fast and slow handlers also run concurrently; total time ≈ max time.
        """
        slow_plugins = [SlowPlugin() for _ in range(3)]
        all_plugins = slow_plugins  # all slow in this example

        coordinator = PluginCoordinator(all_plugins)
        params = MockParams()

        start_time = asyncio.get_event_loop().time()
        await coordinator.emit_event(
            event_name="slow_event",
            action=mock_action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should still be around 0.1s (concurrent)
        assert duration < 0.2

    # The following tests are removed because they verified the semaphore behavior:
    # - test_semaphore_limits_concurrency
    # - test_semaphore_with_max_concurrent_1
    # - test_semaphore_with_max_concurrent_equal_to_plugins
    # - test_semaphore_with_mixed_handlers
    # - test_semaphore_resets_between_events
    #
    # They are no longer applicable.