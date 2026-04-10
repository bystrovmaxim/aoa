# src/action_machine/core/components/connection_validator_protocol.py
"""
Protocol for connection validation component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for validating and normalizing runtime connections against
declared `@connection` requirements on an action class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ConnectionValidator.validate(machine, action, connections, runtime)
                │
                ├── reads declared keys via runtime.connection_keys
                ├── validates presence / absence / extra keys
                ├── validates value types (BaseResourceManager instances)
                └── returns normalized connections dict or raises

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Implementations must raise `ConnectionValidationError` on contract violation.
- The returned dictionary contains only declared keys with valid manager instances.
- Protocol does not enforce specific validation order; only the outcome contract.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Declared and provided keys match -> normalized connections dictionary returned.

Edge case:
- Extra undeclared connection key -> `ConnectionValidationError`.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Protocol does not define how declared keys are obtained; implementations rely
  on the provided `runtime` snapshot or equivalent source.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Connection validator contract.
CONTRACT: validate(machine, action, connections, runtime) -> normalized connections.
INVARIANTS: raises ConnectionValidationError on mismatch; returns normalized dict.
FLOW: input connections -> validation -> normalized connections or error.
FAILURES: ConnectionValidationError for missing/extra/invalid connections.
EXTENSION POINTS: custom validation logic can be injected via implementation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class ConnectionValidatorProtocol(Protocol):
    """Contract for connections validation stage."""

    def validate(
        self,
        machine: object,
        action: BaseAction[BaseParams, BaseResult],
        connections: dict[str, BaseResourceManager] | None,
        runtime: Any,
    ) -> dict[str, BaseResourceManager]:
        """
        Validate and normalize runtime connections.

        Args:
            machine: The executing machine (used for fallback cache retrieval).
            action: Action instance being executed.
            connections: Raw connections dict passed to `run()` (may be None).
            runtime: Pre‑computed action execution cache containing connection keys.

        Returns:
            Normalized connections dictionary with only declared keys and valid
            resource manager instances.

        Raises:
            ConnectionValidationError: If connections do not satisfy declared
                `@connection` requirements.
        """
        ...