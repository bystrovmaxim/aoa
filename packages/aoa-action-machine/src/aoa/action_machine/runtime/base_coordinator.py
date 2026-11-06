# packages/aoa-action-machine/src/aoa/action_machine/runtime/base_coordinator.py
"""
Marker base class for all AOA coordinator primitives.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseCoordinator`` is the common root for primitives that extend or specialise
machine behaviour. Coordinators are plugged into
:class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
and intercept specific phases of action execution — authentication, caching,
saga compensation, and graph construction.

Observation and logging are handled by ``BaseObserver`` subclasses, which carry
no right to modify execution.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Typed marker for ``isinstance`` checks and architectural tooling.
    Common root in the AOA primitive language alongside ``BaseAction``,
    ``BaseResource``, ``BaseAdapter``, ``BaseEntity``, ``BaseObserver``,
    ``BaseIntent``, and ``Lifecycle``.

**Out of scope**
    Any logic — this class is intentionally empty. Each subclass owns its own
    protocol (construction, injection into the machine, runtime behaviour).
"""

from typing import Any

from aoa.action_machine.naming.suffix import require_suffix


class BaseCoordinator:
    """
    AI-CORE-BEGIN
        ROLE: Marker root for all AOA coordinator primitives.
        CONTRACT: No behaviour defined here; subclasses define the coordinator protocol and injection points.
        INVARIANTS: Carries no state.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Refuse a descendant whose name does not end with ``Coordinator``."""
        super().__init_subclass__(**kwargs)
        require_suffix(cls, "BaseCoordinator", "Coordinator")
