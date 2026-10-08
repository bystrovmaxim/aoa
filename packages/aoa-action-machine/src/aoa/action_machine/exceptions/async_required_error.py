# packages/aoa-action-machine/src/aoa/action_machine/exceptions/async_required_error.py
"""``AsyncRequiredError`` — the decorated method must be async."""

from __future__ import annotations


class AsyncRequiredError(TypeError):
    """
    The decorated method is not ``async def``. The engine awaits every aspect, handler and check
    it runs, so a synchronous method would be scheduled and never awaited.
    """

    pass
