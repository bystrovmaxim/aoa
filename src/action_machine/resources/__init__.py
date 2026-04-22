# src/action_machine/resources/__init__.py
"""
ActionMachine resource connection package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package defines public resource-connection contracts used by actions:
base manager abstraction, ``@connection`` declaration API, marker intent, and
the runtime ``connections`` mapping (``dict[str, BaseResourceManager]``).

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

from action_machine.intents.connection.connection_decorator import ConnectionInfo, connection
from action_machine.intents.connection.connection_intent import ConnectionIntent
from action_machine.resources.base_resource_manager import BaseResourceManager

__all__ = [
    "BaseResourceManager",
    "ConnectionInfo",
    "ConnectionIntent",
    "connection",
]
