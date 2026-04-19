# src/action_machine/runtime/components/__init__.py
"""
Re-exports for execution components (canonical modules live on ``action_machine.runtime``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Backward-compatible import path: ``action_machine.runtime.components.*`` maps to
the flat ``action_machine.runtime`` modules.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Compatibility shim for former ``runtime.components`` package layout.
CONTRACT: Re-export same symbols as flat ``action_machine.runtime`` modules.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.runtime.aspect_executor import AspectExecutor
from action_machine.runtime.connection_validator import ConnectionValidator
from action_machine.runtime.dependency_factory_resolver import DependencyFactoryResolver
from action_machine.runtime.error_handler_executor import ErrorHandlerExecutor
from action_machine.runtime.role_checker import RoleChecker
from action_machine.runtime.saga_coordinator import SagaCoordinator
from action_machine.runtime.tools_box_factory import ToolsBoxFactory

__all__ = [
    "AspectExecutor",
    "ConnectionValidator",
    "DependencyFactoryResolver",
    "ErrorHandlerExecutor",
    "RoleChecker",
    "SagaCoordinator",
    "ToolsBoxFactory",
]
