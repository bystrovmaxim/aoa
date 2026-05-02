# src/action_machine/intents/context_requires/context_requires_decorator.py
"""
Decorator ``@context_requires`` — declare aspect access to context fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@context_requires`` is part of ActionMachine intent grammar.
It declares which context fields (``Context``) are required by an aspect or
error handler. At runtime, ``ActionProductMachine`` creates ``ContextView``
with these keys and passes it as last parameter ``ctx``.

Without ``@context_requires``, aspects do not get context access at all.
This enforces least-privilege visibility: aspect sees only declared fields.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Decorator applies to async methods that are aspects
(``@regular_aspect``, ``@summary_aspect``) or error handlers (``@on_error``).
It writes a frozenset of keys to attribute ``func._required_context_keys``.

``@context_requires`` should be closer to function body, while aspect decorator
wraps from outside. This guarantees ``_required_context_keys`` is already set
when aspect decorator validates method signature:

    @regular_aspect("Permission check")      # applied last
    @result_string("status", required=True)  # checker
    @context_requires(Ctx.User.user_id)      # applied first
    async def check_aspect(self, params, state, box, connections, ctx):
        ...

═══════════════════════════════════════════════════════════════════════════════
KEYS ARE DOT-PATH STRINGS
═══════════════════════════════════════════════════════════════════════════════

Each key is a ``"component.field"`` dot-path string for ``Context.resolve()``.
For standard fields, prefer ``Ctx`` constants (IDE autocomplete); for custom
fields, use raw strings:

    @context_requires(Ctx.User.user_id, "user.extra.billing_plan")

Decorator does not validate key existence in ``Context`` because context schema
may be extended by inheritance. Access validation is performed at runtime by
``ContextView.get()``.

═══════════════════════════════════════════════════════════════════════════════
SIGNATURE IMPACT
═══════════════════════════════════════════════════════════════════════════════

Presence of ``@context_requires`` changes expected method parameter count:

    Aspects (``@regular_aspect``, ``@summary_aspect``):
        Without ``@context_requires`` -> 5 parameters: self, params, state, box, connections
        With ``@context_requires``    -> 6 parameters: self, params, state, box, connections, ctx

    Error handlers (``@on_error``):
        Without ``@context_requires`` -> 6 parameters: self, params, state, box, connections, error
        With ``@context_requires``    -> 7 parameters: self, params, state, box, connections, error, ctx

Parameter-count validation is done by ``@regular_aspect``, ``@summary_aspect``,
and ``@on_error`` decorators. They inspect ``_required_context_keys`` and
expect corresponding arity.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        │
        ▼  decorator writes to func._required_context_keys
    frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  @regular_aspect validates signature
    sees _required_context_keys -> expects 6 parameters
        │
        ▼  Interchange wiring records ``context_keys`` on relevant graph edges / companion nodes
    aspect metadata carries frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  ActionProductMachine._call_aspect(...)
    non-empty context_keys -> create ContextView -> pass as ctx
        │
        ▼  aspect calls ctx.get(Ctx.User.user_id)
    ContextView validates allowed_keys -> returns value

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def context_requires(*keys: str) -> Callable[[Any], Any]:
    """
    Method-level decorator declaring context fields required by a callable.

    Writes frozenset of keys to ``func._required_context_keys``.
    ``@regular_aspect``, ``@summary_aspect``, and ``@on_error`` use this marker
    during signature validation and require additional ``ctx`` parameter.

    Args:
        *keys: one or more string keys (dot-path).
            For standard fields, prefer Ctx constants.
            For custom fields, use raw strings
            (for example ``"user.extra.billing_plan"``).

    Returns:
        Decorator that writes ``_required_context_keys`` and returns target unchanged.

    Raises:
        ValueError:
            - no keys provided (empty ``@context_requires()`` call),
            - key is empty or whitespace-only string.
        TypeError:
            - key is not string,
            - target object is not callable.
    """
    # ── Validate at least one key ──
    if not keys:
        raise ValueError(
            "@context_requires: at least one key is required. "
            "Example: @context_requires(Ctx.User.user_id)"
        )

    # ── Validate each key ──
    for i, key in enumerate(keys):
        if not isinstance(key, str):
            raise TypeError(
                f"@context_requires: key [{i}] must be a string, "
                f"got {type(key).__name__}: {key!r}."
            )
        if not key.strip():
            raise ValueError(
                f"@context_requires: key [{i}] cannot be empty. "
                f"Provide a dot-path such as 'user.user_id'."
            )

    # ── Build validated key set ──
    validated_keys: frozenset[str] = frozenset(keys)

    def decorator(func: Any) -> Any:
        """
        Inner decorator applied to target callable.
        """
        if not callable(func):
            raise TypeError(
                f"@context_requires can only be applied to methods/callables. "
                f"Got object of type {type(func).__name__}: {func!r}."
            )

        func._required_context_keys = validated_keys
        return func

    return decorator
