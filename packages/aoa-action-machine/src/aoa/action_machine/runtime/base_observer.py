# packages/aoa-action-machine/src/aoa/action_machine/runtime/base_observer.py
"""
Marker base class for all AOA observer primitives.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseObserver`` is the common root for primitives that observe machine
execution without the right to intervene. Observers receive lifecycle events
and ``box`` messages and produce only side-effects — logs, traces, metrics.

KEY GUARANTEE: Removing all ``BaseObserver`` subclasses leaves system
behaviour unchanged.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Typed marker for ``isinstance`` checks and architectural tooling.
    Common root in the AOA primitive language alongside ``BaseAction``,
    ``BaseResource``, ``BaseAdapter``, ``BaseEntity``, ``BaseCoordinator``,
    ``BaseIntent``, and ``Lifecycle``.

**Out of scope**
    Any logic — this class is intentionally empty. Each subclass owns its own
    protocol (registration, invocation, output target).
"""


class BaseObserver:
    """
    AI-CORE-BEGIN
        ROLE: Marker root for all AOA observer primitives.
        CONTRACT: Side-effects only; never modifies result and never aborts execution.
        INVARIANTS: Removing any BaseObserver leaves system behaviour unchanged.
    AI-CORE-END
    """
