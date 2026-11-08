# packages/aoa-action-machine/src/aoa/action_machine/resources/__init__.py
"""
ActionMachine resource connection package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package defines public resource contracts used by actions:
base manager abstraction, resource marker intent, and the runtime
``connections`` mapping, whose public name is ``Connections``.

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

# Initialize the resource root before metadata can re-enter through a kind module.
from aoa.action_machine.resources.base_resource import BaseResource

# isort: split

from aoa.action_machine.intents.connection.connection_intent import ConnectionIntent
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_gateway import BaseGateway
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources.connections import Connections
from aoa.action_machine.resources.per_call_connection import (
    ConnectionValue,
    PerCallConnection,
    resolve_connections,
    validate_connection_entries,
)

__all__ = [
    "BaseController",
    "BaseGateway",
    "BaseResource",
    "BaseStorage",
    "ConnectionIntent",
    "ConnectionValue",
    "Connections",
    "PerCallConnection",
    "resolve_connections",
    "validate_connection_entries",
]
