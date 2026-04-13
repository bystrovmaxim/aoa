# src/action_machine/intents/on_error/on_error_decorator.py
"""
``@on_error`` decorator for action aspect error handlers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@on_error`` is part of ActionMachine intent grammar. It declares that a
method handles uncaught exceptions raised by regular/summary aspects. When an
aspect fails, ``ActionProductMachine`` finds the first matching handler by
exception type (``isinstance``) and invokes it.

Handler may return ``Result`` to mark error as handled and substitute action
output. If handler raises, runtime wraps it into ``OnErrorHandlerError``.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    exception_types : type[Exception] | tuple[type[Exception], ...]
        One exception type or tuple of types this handler catches.
        Each element must be an ``Exception`` subclass.

    description : str
        Required handler description. Must be non-empty string.
        Used in logs, introspection, and coordinator graph.

═══════════════════════════════════════════════════════════════════════════════
VARIABLE SIGNATURE
═══════════════════════════════════════════════════════════════════════════════

Parameter count depends on ``@context_requires`` on the same method.
``@context_requires`` is applied closer to function body, so
``_required_context_keys`` is already present when ``@on_error`` validates.

    Without ``@context_requires``:
        6 params: self, params, state, box, connections, error

    With ``@context_requires``:
        7 params: self, params, state, box, connections, error, ctx

Handler has its own ``@context_requires`` independent of failed aspect.
If handler needs context, it declares its own keys and receives dedicated
``ContextView``.

Examples:

    # Without context: 6 parameters
    @on_error(ValueError, description="Validation error")
    async def handle_validation_on_error(self, params, state, box, connections, error):
        return MyResult(status="validation_error")

    # With context: 7 parameters
    @on_error(ValueError, description="Validation error with audit")
    @context_requires(Ctx.User.user_id)
    async def handle_validation_on_error(self, params, state, box, connections, error, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return MyResult(status="validation_error", user_id=user_id)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to methods (callables), not classes/properties.
- Method must be async (``async def``).
- Signature: 6 params without ``@context_requires``, 7 with it.
- Method name must end with ``"_on_error"``.
- ``description`` is required and non-empty.
- ``exception_types`` is one Exception type or tuple of Exception types.
- Each element in ``exception_types`` must be an Exception subclass.
- Handlers are NOT inherited from parent Action classes.
- Type-overlap validation (later handler cannot catch same/narrower type) is
  enforced in metadata builder.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @on_error(ValueError, description="Handle validation error")
        │
        ▼  Decorator writes method._on_error_meta
    {"exception_types": (ValueError,), "description": "..."}
        │
        ▼  OnErrorIntentInspector._collect_error_handlers(cls)
    ErrorHandler(..., context_keys=frozenset(...))
        │
        ▼  on_error_intent.validate_error_handlers(cls, error_handlers)
    Validates type overlaps.
        │
        ▼  ActionProductMachine._handle_aspect_error(...)
    If context_keys non-empty -> creates ContextView and passes as ctx.
    Aspect raises ValueError -> runtime matches handler -> calls -> Result.

═══════════════════════════════════════════════════════════════════════════════
HANDLER ORDER AND TYPE OVERLAP
═══════════════════════════════════════════════════════════════════════════════

Handlers are checked top-down in class declaration order.
First match (``isinstance(error, exception_types)``) is invoked.

Valid: specific first, broad fallback second:
    @on_error(ValueError, ...)      <- specific
    @on_error(Exception, ...)       <- fallback

Invalid: broad first, specific second:
    @on_error(Exception, ...)       <- catches everything
    @on_error(ValueError, ...)      <- dead code -> TypeError at metadata build

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    @meta(description="Create order", domain=OrdersDomain)
    @check_roles(NoneRole)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Data validation")
        async def validate_aspect(self, params, state, box, connections):
            if not params.user_id:
                raise ValueError("user_id is required")
            return {"validated_user": params.user_id}

        @summary_aspect("Build result")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(order_id="ORD-1", status="created", total=params.amount)

        @on_error(ValueError, description="Validation error")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="validation_error", total=0)

        # With context:
        @on_error((ConnectionError, TimeoutError), description="Network error")
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def handle_network_on_error(self, params, state, box, connections, error, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            trace = ctx.get(Ctx.Request.trace_id)
            return OrderResult(order_id="ERR", status="network_error", total=0)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

    TypeError: non-callable target, non-async method, wrong parameter count,
        invalid exception_types, non-Exception element, non-string description.
    ValueError: empty/blank description.
    NamingSuffixError: method name does not end with ``"_on_error"``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Method decorator that declares aspect-error handlers.
CONTRACT: Validate handler contract and attach ``_on_error_meta`` metadata.
INVARIANTS: Async method + required suffix + exact parameter contract.
FLOW: decorator validation -> metadata write -> inspector/runtime consumption.
FAILURES: TypeError/ValueError/NamingSuffixError at declaration time.
EXTENSION POINTS: Additional metadata fields via decorator+inspector updates.
AI-CORE-END
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.model.exceptions import NamingSuffixError

# Parameter count without @context_requires.
_BASE_PARAM_COUNT = 6

# Parameter count with @context_requires.
_CTX_PARAM_COUNT = 7

# Parameter names for error messages.
_BASE_PARAM_NAMES = "self, params, state, box, connections, error"
_CTX_PARAM_NAMES = "self, params, state, box, connections, error, ctx"

# Required method name suffix.
_REQUIRED_SUFFIX = "_on_error"


# ============================================================================
# Decorator argument validation
# ============================================================================


def _normalize_exception_types(
    exception_types: type[Exception] | tuple[type[Exception], ...],
) -> tuple[type[Exception], ...]:
    """Normalize exception_types argument to tuple of Exception subclasses."""
    if isinstance(exception_types, type):
        if not issubclass(exception_types, Exception):
            raise TypeError(
                f"@on_error: type {exception_types.__name__} is not an "
                f"Exception subclass."
            )
        return (exception_types,)

    if isinstance(exception_types, tuple):
        if len(exception_types) == 0:
            raise TypeError(
                "@on_error: empty exception type tuple provided. "
                "Specify at least one type."
            )
        for i, exc_type in enumerate(exception_types):
            if not isinstance(exc_type, type):
                raise TypeError(
                    f"@on_error: tuple element [{i}] is not a type, "
                    f"got {type(exc_type).__name__}: {exc_type!r}."
                )
            if not issubclass(exc_type, Exception):
                raise TypeError(
                    f"@on_error: tuple element [{i}] ({exc_type.__name__}) "
                    f"is not an Exception subclass."
                )
        return exception_types

    raise TypeError(
        f"@on_error: first argument must be an Exception type "
        f"or a tuple of Exception types, got "
        f"{type(exception_types).__name__}: {exception_types!r}."
    )


def _exception_types_invariant(
    exception_types: type[Exception] | tuple[type[Exception], ...],
) -> tuple[type[Exception], ...]:
    return _normalize_exception_types(exception_types)


def _validate_description(description: Any) -> None:
    """Validate that description is a non-empty string."""
    if not isinstance(description, str):
        raise TypeError(
            f"@on_error: parameter description must be a string, "
            f"got {type(description).__name__}: {description!r}."
        )
    if not description.strip():
        raise ValueError(
            "@on_error: description cannot be empty. "
            "Provide a handler description."
        )


def _description_invariant(description: Any) -> None:
    _validate_description(description)


def _validate_method(func: Any, description: str) -> None:
    """Validate handler target: callable, async, signature, and name suffix."""
    # Target must be callable.
    if not callable(func):
        raise TypeError(
            f"@on_error can only be applied to methods/callables. "
            f"Got object of type {type(func).__name__}: {func!r}."
        )

    # Handler must be async.
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@on_error(\"{description}\"): method {func.__name__} "
            f"must be async (async def). "
            f"Synchronous handlers are not supported."
        )

    # Parameter count check (with @context_requires awareness).
    has_context = hasattr(func, "_required_context_keys")
    expected_count = _CTX_PARAM_COUNT if has_context else _BASE_PARAM_COUNT
    expected_names = _CTX_PARAM_NAMES if has_context else _BASE_PARAM_NAMES

    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    if param_count != expected_count:
        raise TypeError(
            f"@on_error(\"{description}\"): method {func.__name__} "
            f"must accept {expected_count} parameters "
            f"({expected_names}), got {param_count}."
        )

    # Required method name suffix.
    if not func.__name__.endswith(_REQUIRED_SUFFIX):
        raise NamingSuffixError(
            f"@on_error(\"{description}\"): method '{func.__name__}' "
            f"must end with '{_REQUIRED_SUFFIX}'. "
            f"Rename to '{func.__name__}{_REQUIRED_SUFFIX}' "
            f"or any name with suffix '{_REQUIRED_SUFFIX}'."
        )


def _method_contract_invariant(func: Any, description: str) -> None:
    _validate_method(func, description)


# ============================================================================
# Main decorator
# ============================================================================


def on_error(
    exception_types: type[Exception] | tuple[type[Exception], ...],
    *,
    description: str,
) -> Callable[[Any], Any]:
    """
    Method-level decorator declaring aspect error handler contract.

    Writes metadata to ``method._on_error_meta`` for inspector/runtime use.
    """
    # Validate decorator arguments before method application.
    normalized_types = _exception_types_invariant(exception_types)
    _description_invariant(description)

    def decorator(func: Any) -> Any:
        """Inner decorator applied to handler method."""
        _method_contract_invariant(func, description)

        func._on_error_meta = {
            "exception_types": normalized_types,
            "description": description,
        }

        return func

    return decorator
