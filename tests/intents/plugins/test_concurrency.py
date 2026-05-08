# tests/intents/plugins/test_concurrency.py
"""Tests of parallel and sequential execution of plugin handlers.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks the execution strategy of handlers in the PluginRunContext.
The strategy is selected automatically based on the ignore_exceptions flags
all handlers subscribed to the current event:

- ALL handlers have ignore_exceptions=True:
  Run in parallel via asyncio.gather(return_exceptions=True).
  The total time is the time of the slowest processor. Falling
  handlers do not interrupt the others - their exceptions are suppressed.

- AT LEAST ONE handler has ignore_exceptions=False:
  Run sequentially. Total time is the sum of all delays.
  If a critical handler fails (ignore_exceptions=False)
  the exception is thrown out and interrupts execution.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Parallel execution (all ignore=True):
- Two slow plugins of 50ms each complete in ~50ms (not ~100ms).
- The fast plugin ends along with the slow ones.
- All handlers update their states.
- A falling plugin (ignore=True) does not interrupt the others.

Sequential execution (at least one ignore=False):
- Two slow 50ms plugins execute in ~100ms (total).
- Mixed flags (ignore=True + ignore=False): all handlers
  are executed sequentially and update states.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
A NOTE ABOUT TIMINGS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Timing tests use asyncio.get_event_loop().time() and
threshold values with a margin (0.09s for parallel, 0.09s threshold
for sequential). On slow CI servers, fluttering is possible.
results - if necessary, thresholds can be increased."""

import asyncio

import pytest

from action_machine.plugin.plugin_coordinator import PluginCoordinator

from .conftest import (
    FailingPluginIgnore,
    FastPluginIgnore,
    SlowPluginIgnore,
    SlowPluginNoIgnore,
    emit_global_finish,
)

# ═════════════════════════════════════════════════════════════════════════════
#Concurrency tests (all ignore_exceptions=True)
# ═════════════════════════════════════════════════════════════════════════════


class TestParallelExecution:
    """Tests of parallel execution of handlers.

    All handlers have ignore_exceptions=True → PluginRunContext
    runs them via asyncio.gather(return_exceptions=True)."""

    @pytest.mark.anyio
    async def test_two_slow_plugins_run_in_parallel(self):
        """Two SlowPluginIgnores, 50ms each. When executed in parallel
        total time ~50ms (slowest time), not ~100ms (sum).
        The threshold is 90ms with a margin for the overhead event loop."""
        #Arrange - two slow plugins + one fast
        slow1 = SlowPluginIgnore(delay=0.05)
        slow2 = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()

        coordinator = PluginCoordinator(plugins=[slow1, slow2, fast])
        plugin_ctx = await coordinator.create_run_context()

        #Act - measure execution time
        start = asyncio.get_event_loop().time()
        await emit_global_finish(plugin_ctx)
        elapsed = asyncio.get_event_loop().time() - start

        #Assert - parallel: ~50ms, not ~100ms
        assert elapsed < 0.09, (
            f"Parallel run took {elapsed:.3f}s, expected < 0.09s "
            f"(two 0.05s plugins in parallel)"
        )

        #Assert - all handlers have completed and updated states
        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]

    @pytest.mark.anyio
    async def test_failing_plugin_does_not_interrupt_others(self):
        """FailingPluginIgnore throws RuntimeError with ignore_exceptions=True.
        The error is suppressed, other plugins (SlowPluginIgnore, FastPluginIgnore)
        complete successfully and update their states."""
        #Arrange - slow, fast and crashing plugins (all ignore=True)
        slow = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()
        failing = FailingPluginIgnore()

        coordinator = PluginCoordinator(plugins=[slow, fast, failing])
        plugin_ctx = await coordinator.create_run_context()

        #Act - emit_event should not throw an exception
        await emit_global_finish(plugin_ctx)

        #Assert - successful plugins have updated states
        assert plugin_ctx.get_plugin_state(slow)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]


# ═════════════════════════════════════════════════════════════════════════════
#Sequential execution tests (at least one ignore_exceptions=False)
# ═════════════════════════════════════════════════════════════════════════════


class TestSequentialExecution:
    """Tests of sequential execution of handlers.

    At least one handler has ignore_exceptions=False →
    PluginRunContext runs all handlers sequentially."""

    @pytest.mark.anyio
    async def test_two_slow_plugins_run_sequentially(self):
        """Two SlowPluginNoIgnore of 50ms each. With sequential
        the total execution time is ~100ms (sum), not ~50ms (in parallel).
        Threshold: elapsed >= 0.09s (including overhead)."""
        #Arrange - two slow plugins with ignore=False
        slow1 = SlowPluginNoIgnore(delay=0.05)
        slow2 = SlowPluginNoIgnore(delay=0.05)

        coordinator = PluginCoordinator(plugins=[slow1, slow2])
        plugin_ctx = await coordinator.create_run_context()

        #Act - measure execution time
        start = asyncio.get_event_loop().time()
        await emit_global_finish(plugin_ctx)
        elapsed = asyncio.get_event_loop().time() - start

        #Assert - sequentially: ~100ms, threshold >= 90ms
        assert elapsed >= 0.09, (
            f"Sequential run took {elapsed:.3f}s, expected >= 0.09s "
            f"(two 0.05s plugins sequentially)"
        )

        #Assert - both handlers were executed
        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]

    @pytest.mark.anyio
    async def test_mixed_flags_all_handlers_complete(self):
        """SlowPluginNoIgnore (ignore=False) + FastPluginIgnore (ignore=True).
        Having one ignore=False switches to sequential
        execution. Both handlers complete and update the states."""
        #Arrange - critical slow + non-critical fast
        critical = SlowPluginNoIgnore(delay=0.01)
        metrics = FastPluginIgnore()

        coordinator = PluginCoordinator(plugins=[critical, metrics])
        plugin_ctx = await coordinator.create_run_context()

        #Act - sequential execution due to ignore=False
        await emit_global_finish(plugin_ctx)

        #Assert - both handlers were executed
        assert plugin_ctx.get_plugin_state(critical)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(metrics)["calls"] == ["fast"]
