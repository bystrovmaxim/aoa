# src/action_machine/runtime/components/connection_validator.py
"""
Connection validator component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the connection-validation stage in machine
orchestration. This Step 3 implementation owns validation logic and returns a
normalized connections dictionary for runtime execution.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── ConnectionValidator.validate(action, connections, runtime)
                │
                ├── validates declared/actual key contracts
                ├── validates value types (BaseResourceManager)
                └── returns normalized dictionary

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Validation must preserve existing connection error semantics.
- Returned dictionary is always non-None.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `validate(...)` returns normalized declared connections dictionary.

Edge case:
- Validation raises `ConnectionValidationError` on missing or extra
  connection keys.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This component intentionally does not inspect dependency declarations.
- Contract is limited to `@connection` metadata validation only.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Connection validation component.
CONTRACT: validate(action, connections, runtime) -> normalized connections.
INVARIANTS: key/type checks preserve existing runtime semantics.
FLOW: action + runtime keys + input connections -> validation -> normalized dict.
FAILURES: ConnectionValidationError raised on contract violation.
EXTENSION POINTS: custom validation policy can replace this component.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.exceptions import ConnectionValidationError
from action_machine.resources.base_resource_manager import BaseResourceManager


class ConnectionValidator:
    """Component entry point for connection-validation stage.

    Step 3 implementation owning key/type validation for declared connections.
    """

    def __init__(self, coordinator: GateCoordinator) -> None:
        self._coordinator = coordinator

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> str | None:
        if not declared_keys and actual_keys:
            return (
                f"Action {action_name} does not declare any @connection, "
                f"but received connections with keys: {actual_keys}. "
                f"Remove the connections or add @connection decorators."
            )
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> str | None:
        if declared_keys and not actual_keys:
            return (
                f"Action {action_name} declares connections: {declared_keys}, "
                f"but no connections were passed (None or empty dict). "
                f"Pass connections with keys: {declared_keys}."
            )
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> str | None:
        extra = actual_keys - declared_keys
        if extra:
            return (
                f"Action {action_name} received extra connections: {extra}. "
                f"Only declared: {declared_keys}. Remove the extra keys."
            )
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> str | None:
        missing = declared_keys - actual_keys
        if missing:
            return (
                f"Action {action_name} is missing required connections: {missing}. "
                f"Declared: {declared_keys}, received: {actual_keys}."
            )
        return None

    @staticmethod
    def _validate_connection_value_types(
        action_name: str,
        connections: dict[str, Any],
    ) -> str | None:
        for key, value in connections.items():
            if not isinstance(value, BaseResourceManager):
                return (
                    f"Connection '{key}' for action {action_name} must be an instance "
                    f"of BaseResourceManager, got {type(value).__name__}: {value!r}."
                )
        return None

    def validate(
        self,
        action: BaseAction[BaseParams, BaseResult],
        connections: dict[str, BaseResourceManager] | None,
        runtime: _ConnectionRuntime,
    ) -> dict[str, BaseResourceManager]:
        """Validate connections against declared runtime keys."""
        _ = self._coordinator
        declared_keys: set[str] = set(runtime.connection_keys)
        actual_keys: set[str] = set(connections.keys()) if connections else set()
        action_name: str = action.__class__.__name__

        key_validators = [
            self._validate_no_declarations_but_got_connections,
            self._validate_has_declarations_but_no_connections,
            self._validate_extra_connection_keys,
            self._validate_missing_connection_keys,
        ]
        for validator in key_validators:
            error = validator(action_name, declared_keys, actual_keys)
            if error:
                raise ConnectionValidationError(error)

        if connections:
            type_error = self._validate_connection_value_types(action_name, connections)
            if type_error:
                raise ConnectionValidationError(type_error)

        return connections or {}


class _ConnectionRuntime(Protocol):
    @property
    def connection_keys(self) -> tuple[str, ...]: ...
