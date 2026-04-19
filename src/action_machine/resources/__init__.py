# src/action_machine/resources/__init__.py
"""
ActionMachine resource connection package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package defines public resource-connection contracts used by actions:
base manager abstraction, ``@connection`` declaration API, marker intent, and
typed ``connections`` payload interface.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@connection`` can target only classes that carry ``ConnectionIntent``.
- Connection declarations are represented as immutable ``ConnectionInfo`` records.
- Runtime connection payload must match declared keys and manager types.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class + @connection(...)
              |
              v
    class-level _connection_info scratch
              |
              v
    ConnectionIntentInspector at GraphCoordinator.build()
              |
              v
    Facet snapshot / graph metadata
              |
              v
    ActionProductMachine._check_connections()
              |
              v
    Aspect methods receive connections["key"] manager instances

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    ``@connection(PostgresConnectionManager, key="db")`` declares one resource
    key, runtime validates provided payload, and aspects read ``connections["db"]``.

Edge case:
    Missing/extra connection keys or invalid manager instance type raises
    connection validation errors before action pipeline proceeds.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Concrete integrations (Postgres, Redis, etc.) live in optional integration packages.
- Nested transaction restrictions are enforced by wrapper managers.
- This module exports contracts; it does not implement concrete managers.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public API surface for resource connection declarations and contracts.
CONTRACT: Actions declare resources via @connection and receive typed payload.
INVARIANTS: ConnectionIntent marker required; ConnectionInfo remains immutable.
FLOW: decorator -> inspector snapshot -> runtime payload validation -> usage.
FAILURES: Payload/declaration mismatch surfaces as validation or transaction errors.
EXTENSION POINTS: Add new manager implementations in integrations packages.
AI-CORE-END
"""

from action_machine.intents.connection import ConnectionInfo, connection
from action_machine.legacy.connection_intent import ConnectionIntent
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connections_typed_dict import Connections

__all__ = [
    "BaseResourceManager",
    "ConnectionInfo",
    "ConnectionIntent",
    "Connections",
    "connection",
]
