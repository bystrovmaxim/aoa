# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_condition_async_error.py
"""AccessConditionAsyncError."""

from collections.abc import Callable


class AccessConditionAsyncError(TypeError):
    """
    Raised when a `grant(when=...)` or `guard=` condition is defined as `async def`.

    An unawaited coroutine object is always truthy, so an async condition would
    silently pass every check instead of being evaluated. Checked at class
    definition time, not at runtime.
    """

    def __init__(self, condition_name: str, func: Callable[..., object]) -> None:
        func_name = getattr(func, "__qualname__", repr(func))
        super().__init__(
            f"{condition_name}={func_name} must be a synchronous callable returning bool, "
            f"not `async def` (an unawaited coroutine is always truthy and would silently "
            f"pass every check)."
        )
        self.condition_name = condition_name
        self.func = func
