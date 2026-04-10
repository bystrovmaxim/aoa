# src/action_machine/core/components/connection_validator.py
"""
Connection validator component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the connection-validation stage in the
machine orchestration. Currently delegates to existing machine internals; full
logic migration happens in a later step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ConnectionValidator.validate(machine, action, connections, runtime)
                │
                └── machine._check_connections(...)   // temporary delegation

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Component receives a reference to `GateCoordinator` for future snapshot reads.
- Delegation target remains stable during scaffolding phase.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `validate(...)` returns normalized declared connections dictionary.

Edge case:
- Delegated validation raises `ConnectionValidationError` on missing or extra
  connection keys.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Implementation is temporary and delegates to a private machine method.
- ConnectionValidationError propagation matches existing machine behavior.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Connection validation component scaffolding.
CONTRACT: validate(machine, action, connections, runtime) -> normalized connections.
INVARIANTS: GateCoordinator injected; delegation is temporary.
FLOW: machine -> ConnectionValidator.validate -> legacy machine method.
FAILURES: ConnectionValidationError raised on contract violation.
EXTENSION POINTS: future replacement of delegation with direct snapshot-based validation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class ConnectionValidator:
    """Component entry point for connection-validation stage.

    This is a scaffolding implementation that delegates to the existing
    machine's internal method. Full migration of connection-validation logic
    will happen in a subsequent step.
    """

    def __init__(self, coordinator: GateCoordinator) -> None:
        self._coordinator = coordinator

    def validate(
        self,
        machine: object,
        action,
        connections: dict[str, BaseResourceManager] | None,
        runtime,
    ) -> dict[str, BaseResourceManager]:
        """Delegate connection checks to current machine logic."""
        _ = self._coordinator  # kept for future use
        return machine._check_connections(action, connections, runtime)  # noqa: SLF001