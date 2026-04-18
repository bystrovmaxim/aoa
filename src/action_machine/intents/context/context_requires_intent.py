# src/action_machine/intents/context/context_requires_intent.py
"""
Context-requires intent marker and marker-enforcement validator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ContextRequiresIntent`` is marker mixin indicating that a class may use
``@context_requires`` on aspects, error handlers, and compensators.

If methods declare context keys (``_required_context_keys``), build-time
validators require class inheritance from ``ContextRequiresIntent``.
Missing marker raises ``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
BASEACTION MRO INTENTS
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` inherits multiple intent markers. Each marker defines one
grammar segment: which decorators are allowed and what build-time validators
enforce in ``GraphCoordinator.build()``:

    ActionMetaIntent       -> @meta
    RoleIntent             -> @check_roles
    DependencyIntent       -> @depends
    CheckerIntent          -> result_* checkers
    AspectIntent           -> @regular_aspect / @summary_aspect
    CompensateIntent       -> @compensate
    ConnectionIntent       -> @connection
    OnErrorIntent          -> @on_error
    ContextRequiresIntent  -> @context_requires

Common pattern: empty marker classes without behavior; ``issubclass`` links
type to declaration contract and validator set.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaIntent,
        RoleIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        CompensateIntent,
        ConnectionIntent,
        OnErrorIntent,
        ContextRequiresIntent,        <- intent: @context_requires grammar
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Permission check")
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def check_permissions_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            ...

    # Build-time validator:
    #   1. Finds _required_context_keys on check_permissions_aspect.
    #   2. Checks issubclass(CreateOrderAction, ContextRequiresIntent) -> True.
    #   3. Persists context_keys into aspect snapshot.
    #
    # Runtime aspect invocation:
    #   1. Reads aspect_meta.context_keys -> frozenset({"user.user_id", "user.roles"}).
    #   2. Creates ContextView(context, aspect_meta.context_keys).
    #   3. Passes ctx_view as 6th argument.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction already inherits ContextRequiresIntent, so every action class
    # supports @context_requires declarations by default.

    # Aspect with context access:
    @regular_aspect("Audit")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user, "from_ip": ip}

    # Aspect without context access (standard signature):
    @regular_aspect("Total calculation")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- If any collected method has ``context_keys``, class must inherit marker.
- Marker is behavior-free and serves only contract/validation semantics.
- Validation scope includes aspects, error handlers, and compensators.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``TypeError`` when context-requires usage is declared without marker.
- This module validates declaration topology only; runtime access checks are in
  ``ContextView``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Marker + validator module for @context_requires grammar.
CONTRACT: Require ContextRequiresIntent when context keys are declared.
INVARIANTS: Deterministic marker enforcement across aspect/error/compensator facets.
FLOW: collected metadata -> marker check -> validated snapshots -> runtime ContextView.
FAILURES: TypeError for missing marker inheritance.
EXTENSION POINTS: Applies to new method categories carrying context_keys.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any


class ContextRequiresIntent:
    """
    Marker mixin declaring support for ``@context_requires`` declarations.

    AI-CORE-BEGIN
    ROLE: Context-access grammar marker for action classes.
    CONTRACT: Classes with context-requires declarations must include marker.
    INVARIANTS: Pure marker with no runtime behavior/state.
    AI-CORE-END
    """

    pass


def _has_any_context_keys(
    aspects: list[Any],
    error_handlers: list[Any],
    compensators: list[Any],
) -> bool:
    for aspect in aspects:
        if aspect.context_keys:
            return True
    for handler in error_handlers:
        if handler.context_keys:
            return True
    for comp in compensators:
        if comp.context_keys:
            return True
    return False


def require_context_requires_intent_marker(
    cls: type,
    aspects: list[Any],
    error_handlers: list[Any],
    compensators: list[Any],
) -> None:
    """Require marker inheritance when context keys are declared."""
    if _has_any_context_keys(aspects, error_handlers, compensators) and not issubclass(
        cls, ContextRequiresIntent
    ):
        methods_with_ctx: list[str] = []
        for a in aspects:
            if a.context_keys:
                methods_with_ctx.append(a.method_name)
        for h in error_handlers:
            if h.context_keys:
                methods_with_ctx.append(h.method_name)
        for c in compensators:
            if c.context_keys:
                methods_with_ctx.append(c.method_name)
        methods_str = ", ".join(methods_with_ctx)
        raise TypeError(
            f"Class {cls.__name__} declares methods with @context_requires "
            f"({methods_str}) but does not inherit ContextRequiresIntent. "
            f"The @context_requires grammar is valid only when marker intent "
            f"is present in MRO. Use BaseAction or add ContextRequiresIntent "
            f"to the inheritance chain."
        )
