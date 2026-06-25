# packages/aoa-action-machine/src/aoa/action_machine/runtime/base_controller.py
"""
Marker base class for all AOA controller primitives.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseController`` is the common root for primitives that govern directed
execution flow or state-machine transitions. Concrete controllers declare a
graph at class-definition time (as a class variable built with a fluent API)
and apply it at runtime — either to enforce valid state transitions on an
entity, or to orchestrate an ordered sequence of actions.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Typed marker for ``isinstance`` checks and architectural tooling.
    Common root in the AOA primitive language alongside ``BaseAction``,
    ``BaseResource``, ``BaseAdapter``, ``BaseEntity``, and ``BaseCoordinator``.

**Out of scope**
    Any logic — this class is intentionally empty. Each subclass owns its own
    lifecycle (template construction, compilation, runtime invocation).
"""


class BaseController:
    """
    AI-CORE-BEGIN
        ROLE: Marker root for all AOA controller primitives.
        CONTRACT: No behaviour defined here; subclasses provide template construction and runtime invocation.
        INVARIANTS: Carries no state.
    AI-CORE-END
    """
