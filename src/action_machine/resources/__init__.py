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
