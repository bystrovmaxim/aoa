# src/action_machine/auth/__init__.py
"""Role marker types and authentication coordinator contracts."""

from __future__ import annotations

import importlib
from typing import Any

# Role graph only: loading ``Authenticator`` / ``AuthCoordinator`` here would pull
# ``UserInfo`` / ``Context`` while ``user_info`` is still importing ``BaseRole``
# (package ``__init__`` runs before ``base_role`` finishes).
from action_machine.auth.base_role import BaseRole
from action_machine.auth.system_role import SystemRole
from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.any_role import AnyRole
from action_machine.auth.none_role import NoneRole
from action_machine.auth.role_graph_node import RoleGraphNode

_LAZY_AUTH_PIPELINE: dict[str, tuple[str, str]] = {
    "Authenticator": ("action_machine.auth.authenticator", "Authenticator"),
    "AuthCoordinator": ("action_machine.auth.auth_coordinator", "AuthCoordinator"),
    "ContextAssembler": ("action_machine.auth.auth_coordinator", "ContextAssembler"),
    "CredentialExtractor": ("action_machine.auth.auth_coordinator", "CredentialExtractor"),
    "NoAuthCoordinator": ("action_machine.auth.auth_coordinator", "NoAuthCoordinator"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_AUTH_PIPELINE:
        mod_path, attr = _LAZY_AUTH_PIPELINE[name]
        module = importlib.import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


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
    "SystemRole",
]
