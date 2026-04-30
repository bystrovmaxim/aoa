# src/action_machine/intents/check_roles/__init__.py
"""
ActionMachine authentication package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides authentication coordinators, role **marker types** (``BaseRole``),
decorators (``@check_roles``, ``@role_mode``), and abstract interfaces for
credential extraction, verification, and context assembly.

═══════════════════════════════════════════════════════════════════════════════
ROLE TYPE HIERARCHY (ONE CLASS ≈ ONE MODULE)
═══════════════════════════════════════════════════════════════════════════════

Role hierarchy modules live under ``src/action_machine/auth/`` (one class ≈ one module):

::

    BaseRole (ABC)                 → base_role.py
    ├── SystemRole (ABC)           → system_role.py
    │   ├── NoneRole (sealed)      → none_role.py
    │   └── AnyRole (sealed)       → any_role.py
    └── ApplicationRole (ABC)      → application_role.py
        └── …                      → project-specific application roles

- **``SystemRole`` / ``NoneRole`` / ``AnyRole``** — engine sentinels for
  ``@check_roles`` only. They are **not** placed in ``UserInfo.roles``.
- **``ApplicationRole``** — abstract root for types that **may** appear in
  ``UserInfo.roles`` (assignable business roles).

Who satisfies ``@check_roles(X)`` is determined **only** by **subclassing**
(``issubclass`` / MRO). There is no separate role-composition or bitmask field.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────┐    ┌───────────────┐    ┌──────────────────┐
    │ CredentialExtractor │ -> │ Authenticator │ -> │ ContextAssembler │
    └──────────┬──────────┘    └───────┬───────┘    └────────┬─────────┘
               └────────────────────────┴─────────────────────┘
                                    |
                                    v
                           AuthCoordinator.process()
                                    |
                                    v
                          Context(UserInfo.roles)

    Role model (types, not strings at runtime in snapshots):

        RoleModeIntent  ◀──  BaseRole  ◀──  your concrete *Role classes
              ▲                      │
              │               @role_mode(RoleMode.…)
              │                      │
        @role_mode                 subclassing (MRO) for implied roles
              │
        ContextAssembler maps external credentials → UserInfo(roles=(…BaseRole types))

        Action classes (CheckRolesIntent) + @check_roles(AdminRole | [RoleA, RoleB] | …)
              │
              ├── RoleClassInspector → ``role_class`` vertex **only** for ``ApplicationRole``
              │                         (validates every ``BaseRole`` subclass but does not materialize them)
              │
              ├── RoleIntentInspector → ``role`` snapshot on the action + ``requires_role`` edges
              │                         (action → anchor ``role_class``; no extra vertex for the decorator)
              │
              └── RoleModeIntentInspector → ``role_mode`` snapshot + ``mode`` merged onto that anchor row
              │
              ▼
        GraphCoordinator.build() → RoleChecker at run time

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``AuthCoordinator`` / ``NoAuthCoordinator``: context production policy.
- ``CredentialExtractor`` / ``Authenticator`` / ``ContextAssembler``:
  extension interfaces for auth pipeline steps.
- ``BaseRole`` + ``RoleModeIntent``: typed role model and lifecycle marker.
- ``check_roles`` / ``role_mode``: declarative access-control decorators.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.check_roles import (
        AnyRole,
        BaseRole,
        NoneRole,
        RoleMode,
        check_roles,
        role_mode,
    )

    @role_mode(RoleMode.ALIVE)
    class AdminRole(BaseRole):
        name = "admin"
        description = "Administrator access."

    @check_roles(AdminRole)
    class AdminAction(BaseAction[...]):
        ...

    @check_roles(NoneRole)
    class PingAction(BaseAction[...]):
        ...

    auth = AuthCoordinator(extractor, authenticator, assembler)
    context = await auth.process(request)
"""

from __future__ import annotations

# pylint: disable=undefined-all-variable
# ``__all__`` lists lazy names resolved in :func:`__getattr__` (PEP 562).
import importlib
from typing import Any

from action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from action_machine.intents.role_mode.role_mode_intent import RoleModeIntent

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AnyRole": ("action_machine.auth.any_role", "AnyRole"),
    "AuthCoordinator": ("action_machine.auth.auth_coordinator", "AuthCoordinator"),
    "Authenticator": ("action_machine.auth.authenticator", "Authenticator"),
    "BaseRole": ("action_machine.auth.base_role", "BaseRole"),
    "ContextAssembler": ("action_machine.auth.auth_coordinator", "ContextAssembler"),
    "CredentialExtractor": ("action_machine.auth.auth_coordinator", "CredentialExtractor"),
    "NoAuthCoordinator": ("action_machine.auth.auth_coordinator", "NoAuthCoordinator"),
    "NoneRole": ("action_machine.auth.none_role", "NoneRole"),
    "check_roles": ("action_machine.intents.check_roles.check_roles_decorator", "check_roles"),
    "RoleMode": ("action_machine.intents.role_mode.role_mode_decorator", "RoleMode"),
    "role_mode": ("action_machine.intents.role_mode.role_mode_decorator", "role_mode"),
    "RoleGraphNode": (
        "action_machine.graph_model.nodes.role_graph_node",
        "RoleGraphNode",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy imports avoid circular init when ``base_role`` loads ``RoleModeIntent``."""
    if name in _LAZY_EXPORTS:
        mod_path, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = [
    "AnyRole",
    "AuthCoordinator",
    "Authenticator",
    "BaseRole",
    "CheckRolesIntent",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "NoneRole",
    "RoleGraphNode",
    "RoleMode",
    "RoleModeIntent",
    "check_roles",
    "role_mode",
]
