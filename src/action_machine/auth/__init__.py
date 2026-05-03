# src/action_machine/auth/__init__.py
"""Role marker types and authentication coordinator contracts."""

from __future__ import annotations

from action_machine.auth.any_role import AnyRole
from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.auth_coordinator import (
    AuthCoordinator,
    ContextAssembler,
    CredentialExtractor,
    NoAuthCoordinator,
)
from action_machine.auth.authenticator import Authenticator
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole
from action_machine.auth.system_role import SystemRole
from action_machine.graph_model.inspectors.role_graph_node_inspector import (
    RoleGraphNodeInspector,
)
from action_machine.graph_model.nodes.role_graph_node import RoleGraphNode

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
