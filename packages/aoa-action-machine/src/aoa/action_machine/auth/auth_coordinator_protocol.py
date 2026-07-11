# packages/aoa-action-machine/src/aoa/action_machine/auth/auth_coordinator_protocol.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
AuthCoordinatorProtocol — typed surface for the ``auth_coordinator=`` contract.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every adapter (``BaseAdapter`` and its concrete subclasses) accepts an
``auth_coordinator`` that is duck-typed against a single async ``process``
method — ``AuthCoordinator``, ``NoAuthCoordinator``, and any fully custom
coordinator (see ``docs/how-to/authoring-auth-coordinator.md``) all satisfy
this without a shared base class. Before this protocol, that contract was
typed ``Any`` everywhere, so a typo'd method name or wrong signature on a
custom coordinator was invisible to mypy/IDEs until runtime. Purely additive
typing — structural (``Protocol``), so every existing coordinator already
satisfies it with zero code changes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    AuthCoordinatorProtocol (typing.Protocol)
              │
              △ structural match, no inheritance required
              │
    AuthCoordinator · NoAuthCoordinator · any duck-typed custom coordinator
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aoa.action_machine.context.context import Context


@runtime_checkable
class AuthCoordinatorProtocol(Protocol):
    """
    AI-CORE-BEGIN
    ROLE: Typed contract for objects usable as ``auth_coordinator=`` on any adapter.
    CONTRACT: ``process(request_data)`` returns ``Context`` on success or ``None`` when the flow cannot continue; never raises for "no/invalid credentials" (that is ``None``, not an exception).
    INVARIANTS: Structural subtyping — no inheritance required, only a matching ``process`` method.
    AI-CORE-END
    """

    async def process(self, request_data: Any) -> Context | None:
        """Build a ``Context`` from protocol-specific request data, or ``None`` if the flow cannot continue."""
        ...
