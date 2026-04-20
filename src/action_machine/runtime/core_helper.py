# src/action_machine/runtime/core_helper.py
"""
Core helper utilities for ActionMachine runtime.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module hosts small runtime utilities shared across execution paths.
Current helper bridges synchronous callables into async contexts without
blocking the event loop.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    async caller
        |
        v
    CoreHelper.run_in_thread(func, *args)
        |
        v
    loop.run_in_executor(None, func, *args)
        |
        v
    await result or re-raise callable exception

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    ``await CoreHelper.run_in_thread(cpu_bound_fn, a, b)`` returns callable result.

Edge case:
    If callable raises, the same exception is surfaced to async caller.
"""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class CoreHelper:
    """Collection of runtime helper static methods."""

    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args: Any) -> T:
        """
        Run a synchronous blocking callable in a background thread.

        Useful for CPU-bound or sync-library calls inside async runtime code.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
