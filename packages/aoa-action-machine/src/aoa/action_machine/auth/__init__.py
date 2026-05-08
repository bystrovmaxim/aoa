# packages/aoa-action-machine/src/aoa/action_machine/auth/__init__.py
"""Role marker types and authentication coordinator contracts."""

from __future__ import annotations

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.auth.auth_coordinator import (
    AuthCoordinator,
    ContextAssembler,
    CredentialExtractor,
    NoAuthCoordinator,
)
from aoa.action_machine.auth.authenticator import Authenticator
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.none_role import NoneRole
from aoa.action_machine.auth.system_role import SystemRole
from aoa.action_machine.graph_model.inspectors.role_graph_node_inspector import (
    RoleGraphNodeInspector,
)
from aoa.action_machine.graph_model.nodes.role_graph_node import RoleGraphNode

__all__ = [
    "AnyRole",
    "ApplicationRole",
    "AuthCoordinator",
    "Authenticator",
    "BaseRole",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "NoneRole",
    "RoleGraphNode",
    "RoleGraphNodeInspector",
    "SystemRole",
]
