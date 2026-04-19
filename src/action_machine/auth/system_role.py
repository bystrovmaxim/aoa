# src/action_machine/auth/system_role.py
"""
``SystemRole`` root for engine-level sentinel roles.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define an abstract hierarchy branch for engine policy roles used in
``@check_roles`` specifications (for example, ``NoneRole`` and ``AnyRole``).
These roles are protocol/runtime policy markers, not user-assignable roles.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- System sentinel roles inherit from ``SystemRole``.
- ``SystemRole`` descendants are not intended for ``UserInfo.roles`` storage.
- Declared with ``@role_mode(RoleMode.ALIVE)`` as active root branch.
- The class is abstract and serves as role taxonomy boundary.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole
       |
       v
    SystemRole (this class)
       |
       +--> NoneRole (public/no-auth policy)
       |
       +--> AnyRole  (any-assignable-role policy)
       |
       v
    @check_roles sentinel specifications

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Abstract taxonomy root; not meant for direct role assignment.
- Authorization semantics are enforced by role-check runtime, not this class.

AI-CORE-BEGIN
ROLE: Engine-sentinel role hierarchy root.
CONTRACT: Provide stable parent for non-assignable policy roles.
INVARIANTS: ALIVE mode and exclusion from UserInfo.roles assignment payload.
AI-CORE-END

See hierarchy docs in ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from abc import ABC

from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class SystemRole(BaseRole, ABC):
    """
    Abstract root of role types intended only for ``@check_roles`` sentinel specs.

    AI-CORE-BEGIN
    ROLE: Parent class for engine policy roles.
    CONTRACT: Concrete sentinel roles inherit from this branch.
    INVARIANTS: Not assigned to users; used in authorization declarations.
    AI-CORE-END
    """

    name = "__system_root__"
    description = (
        "Intermediate root for engine sentinel roles (not assignable to UserInfo.roles)."
    )
