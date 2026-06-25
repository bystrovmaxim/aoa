# packages/aoa-action-machine/src/aoa/action_machine/intents/base_intent.py
"""
Marker base class for all AOA intent primitives.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseIntent`` is the common root for all declarative intent marker mixins.
Each ``*Intent`` subclass declares that a class participates in a specific
AOA grammar — roles, aspects, caching, dependencies, and so on.

Intent markers carry no runtime behaviour. They are inspected via
``issubclass`` / MRO checks inside decorators and graph inspectors.

KEY PROPERTY: ``BaseIntent`` is orthogonal to every other AOA primitive —
it may be mixed into ``BaseAction``, ``BaseEntity``, or any other class
without creating dependencies between those primitives.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Typed marker for ``issubclass`` checks and architectural tooling.
    Common root that makes all intent primitives discoverable as a group.

**Out of scope**
    Any logic — this class is intentionally empty. Each subclass owns its own
    marker semantics and class-level data contract (e.g. ``_role_info``).
"""


class BaseIntent:
    """
    AI-CORE-BEGIN
        ROLE: Marker root for all AOA intent primitives.
        CONTRACT: Declarative mixin only; carries no runtime behaviour.
        INVARIANTS: Can be mixed into any primitive; orthogonal to all others.
    AI-CORE-END
    """
