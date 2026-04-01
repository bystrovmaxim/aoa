# tests2/core/test_core_helper.py
"""
Tests for CoreHelper — utility class with async thread execution.

CoreHelper provides a single static method run_in_thread that offloads
synchronous blocking functions to a thread pool executor, preventing
event loop starvation. The method uses asyncio.get_running_loop() and
loop.run_in_executor(None, func, *args).

Scenarios covered:
    - Synchronous function executes and returns its result.
    - Arguments are passed correctly to the target function.
    - Multiple arguments are forwarded in order.
    - Blocking function does not block the event loop.
    - Exceptions from the target function propagate to the caller.
"""

import asyncio
import time

import pytest

from action_machine.core.core_helper import CoreHelper

# ═════════════════════════════════════════════════════════════════════════════
# Basic execution
# ═════════════════════════════════════════════════════════════════════════════


class TestRunInThread:
    """Verify that run_in_thread offloads work and returns results."""

    @pytest.mark.asyncio
    async def test_returns_result(self) -> None:
        """A simple synchronous function returns its value through the executor."""

        def add(a: int, b: int) -> int:
            return a + b

        result = await CoreHelper.run_in_thread(add, 3, 7)
        assert result == 10

    @pytest.mark.asyncio
    async def test_single_argument(self) -> None:
        """A function with one argument receives it correctly."""

        def double(x: int) -> int:
            return x * 2

        result = await CoreHelper.run_in_thread(double, 21)
        assert result == 42

    @pytest.mark.asyncio
    async def test_no_arguments(self) -> None:
        """A function with no arguments executes correctly."""

        def greeting() -> str:
            return "hello"

        result = await CoreHelper.run_in_thread(greeting)
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_string_processing(self) -> None:
        """String operations work correctly in the thread."""

        def upper(text: str) -> str:
            return text.upper()

        result = await CoreHelper.run_in_thread(upper, "test")
        assert result == "TEST"


# ═════════════════════════════════════════════════════════════════════════════
# Non-blocking behavior
# ═════════════════════════════════════════════════════════════════════════════


class TestNonBlocking:
    """Verify that the event loop is not blocked during execution."""

    @pytest.mark.asyncio
    async def test_does_not_block_event_loop(self) -> None:
        """A blocking sleep in the thread does not prevent other coroutines."""

        def slow_func() -> str:
            time.sleep(0.05)
            return "done"

        # Run the blocking function and a quick coroutine concurrently
        quick_result = []

        async def quick_task() -> None:
            quick_result.append("quick")

        results = await asyncio.gather(
            CoreHelper.run_in_thread(slow_func),
            quick_task(),
        )

        assert results[0] == "done"
        assert quick_result == ["quick"]


# ═════════════════════════════════════════════════════════════════════════════
# Exception propagation
# ═════════════════════════════════════════════════════════════════════════════


class TestExceptionPropagation:
    """Verify that exceptions from the target function reach the caller."""

    @pytest.mark.asyncio
    async def test_value_error_propagates(self) -> None:
        """A ValueError raised inside the thread propagates to await."""

        def fail() -> None:
            raise ValueError("broken")

        with pytest.raises(ValueError, match="broken"):
            await CoreHelper.run_in_thread(fail)

    @pytest.mark.asyncio
    async def test_type_error_propagates(self) -> None:
        """A TypeError raised inside the thread propagates to await."""

        def bad_add(a: int, b: int) -> int:
            return a + b

        with pytest.raises(TypeError):
            await CoreHelper.run_in_thread(bad_add, "not_int", 5)
