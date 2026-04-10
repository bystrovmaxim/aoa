# src/action_machine/core/components/role_checker.py
"""
Role checker component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the role-check stage in the machine
orchestration. Currently delegates to existing machine internals; full logic
migration happens in a later step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── RoleChecker.check(machine, action, context, runtime)
                │
                └── machine._check_action_roles(...)   // temporary delegation

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Component receives a reference to `GateCoordinator` for future snapshot reads.
- Delegation target remains stable during scaffolding phase.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `RoleChecker.check(...)` delegates to `machine._check_action_roles(...)` and
  returns `None` when access is allowed.

Edge case:
- Delegated check raises `AuthorizationError` for missing required role.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Implementation is temporary and delegates to a private machine method.
- AuthorizationError propagation matches existing machine behavior.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role-check component scaffolding.
CONTRACT: check(machine, action, context, runtime) -> None or AuthorizationError.
INVARIANTS: GateCoordinator injected; delegation is temporary.
FLOW: machine -> RoleChecker.check -> legacy machine method.
FAILURES: AuthorizationError raised on role mismatch.
EXTENSION POINTS: future replacement of delegation with direct snapshot-based check.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.context.context import Context
from action_machine.metadata.gate_coordinator import GateCoordinator


class RoleChecker:
    """Component entry point for role-check stage.

    This is a scaffolding implementation that delegates to the existing
    machine's internal method. Full migration of role-checking logic will
    happen in a subsequent step.
    """

    def __init__(self, coordinator: GateCoordinator) -> None:
        self._coordinator = coordinator

    def check(self, machine: object, action, context: Context, runtime) -> None:
        """Delegate role checking to current machine logic."""
        _ = self._coordinator  # kept for future use
        machine._check_action_roles(action, context, runtime)  # noqa: SLF001