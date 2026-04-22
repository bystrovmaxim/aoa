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

"""

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connections_typed_dict import Connections
from action_machine.intents.connection.connection_decorator import ConnectionInfo, connection
from action_machine.intents.connection.connection_intent import ConnectionIntent

__all__ = [
    "BaseResourceManager",
    "ConnectionInfo",
    "ConnectionIntent",
    "Connections",
    "connection",
]
