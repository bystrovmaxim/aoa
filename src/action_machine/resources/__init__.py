# src/action_machine/resources/__init__.py
"""
ActionMachine resource connection package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package defines public resource contracts used by actions:
base manager abstraction, resource marker intent, and the runtime
``connections`` mapping (``dict[str, BaseResource]``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action class
              |
              v
    runtime ``connections`` mapping
              |
              v
    Aspect methods receive manager instances

"""

from action_machine.intents.connection.connection_intent import ConnectionIntent
from action_machine.resources.base_resource import BaseResource

__all__ = [
    "BaseResource",
    "ConnectionIntent",
]
