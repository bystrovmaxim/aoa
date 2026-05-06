# src/action_machine/runtime/connection_validator.py
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
        └── ConnectionValidator.validate(action, connections, action_node)
                │
                ├── validates declared/actual key contracts
                ├── validates value types (BaseResource)
                └── returns normalized dictionary

"""

from __future__ import annotations

from typing import Any

from action_machine.exceptions.connection_validation_error import ConnectionValidationError
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource import BaseResource


class ConnectionValidator:
    """Validate ``connections`` keys and ``BaseResource`` values for a machine run."""

    @staticmethod
    # Declared none, caller passed at least one key — reject.
    def _validate_no_declarations_but_got_connections(
        action_name: str,
        declared_keys: frozenset[str],
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
    # Declared at least one key, caller passed none — reject.
    def _validate_has_declarations_but_no_connections(
        action_name: str,
        declared_keys: frozenset[str],
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
    # Caller keys must not exceed declared set.
    def _validate_extra_connection_keys(
        action_name: str,
        declared_keys: frozenset[str],
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
    # Every declared key must be present in the caller mapping.
    def _validate_missing_connection_keys(
        action_name: str,
        declared_keys: frozenset[str],
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
    # Each value must be a BaseResource instance.
    def _validate_connection_value_types(
        action_name: str,
        connections: dict[str, Any],
    ) -> str | None:
        for key, value in connections.items():
            if not isinstance(value, BaseResource):
                return (
                    f"Connection '{key}' for action {action_name} must be an instance "
                    f"of BaseResource, got {type(value).__name__}: {value!r}."
                )
        return None

    def validate(
        self,
        action: BaseAction[BaseParams, BaseResult],
        connections: dict[str, BaseResource] | None,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> dict[str, BaseResource]:
        """Validate connections against keys from ``action_node.connection_keys()``."""
        declared_keys = action_node.connection_keys()
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
