# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/__init__.py
"""
ActionMachine authentication package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides role **marker types** (``BaseRole``), access-control decorators
(``@check_roles``, ``@role_mode``), and the role graph contract.

═══════════════════════════════════════════════════════════════════════════════
ROLE TYPE HIERARCHY (ONE CLASS ≈ ONE MODULE)
═══════════════════════════════════════════════════════════════════════════════

Role hierarchy modules live under ``packages/aoa-action-machine/src/aoa/action_machine/auth/`` (one class ≈ one module):

::

    BaseRole (ABC)                 → base_role.py
    ├── SystemRole (ABC)           → system_role.py
    │   ├── GuestRole (sealed)     → guest_role.py
    │   └── AnyRole (sealed)       → any_role.py
    └── ApplicationRole (ABC)      → application_role.py
        └── …                      → project-specific application roles

- **``SystemRole`` / ``GuestRole`` / ``AnyRole``** — engine sentinels for
  ``@check_roles`` only. They are **not** placed in ``UserInfo.roles``.
- **``ApplicationRole``** — abstract root for types that **may** appear in
  ``UserInfo.roles`` (assignable business roles).

Who satisfies ``@check_roles(X)`` is determined **only** by **subclassing**
(``issubclass`` / MRO). There is no separate role-composition or bitmask field.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Role model (types, not strings at runtime in snapshots):

        RoleModeIntent  ◀──  BaseRole  ◀──  your concrete *Role classes
              ▲                      │
              │               @role_mode(RoleMode.…)
              │                      │
        @role_mode                 subclassing (MRO) for implied roles
              │
        ContextAssembler maps external credentials → UserInfo(roles=(…BaseRole types))

        Action classes (:class:`~aoa.action_machine.intents.check_roles.check_roles_intent.CheckRolesIntent`) with ``@check_roles``
              │
              ▼
        Interchange ``ActionGraphNode`` + ``RoleGraphEdge`` topology
              │
              ▼
        :class:`~aoa.action_machine.runtime.role_checker.RoleChecker` at runtime

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.check_roles import (
        AnyRole,
        BaseRole,
        GuestRole,
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

    @check_roles(GuestRole)
    class PingAction(BaseAction[...]):
        ...
"""

from __future__ import annotations

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.intents.role_mode.role_mode_intent import RoleModeIntent

__all__ = [
    "AnyRole",
    "BaseRole",
    "CheckRolesIntent",
    "GuestRole",
    "RoleMode",
    "RoleModeIntent",
    "check_roles",
    "role_mode",
]
