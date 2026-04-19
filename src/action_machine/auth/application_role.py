# src/action_machine/auth/application_role.py
"""
``ApplicationRole`` root for assignable business roles.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define a common abstract root for roles that may be assigned to authenticated
users and stored in ``UserInfo.roles``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Application roles should inherit from ``ApplicationRole`` (not directly from
  ``BaseRole``).
- Marked with ``@role_mode(RoleMode.ALIVE)`` as default active role branch.
- This class is abstract and acts as hierarchy boundary, not as a concrete role.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole
       |
       v
    ApplicationRole (this class)
       |
       v
    Concrete app roles (AdminRole, ManagerRole, ...)
       |
       v
    UserInfo.roles + @check_roles runtime checks

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Abstract hierarchy node; intended for inheritance only.
- Policy semantics (allow/deny) are enforced by role-check runtime, not here.

AI-CORE-BEGIN
ROLE: Assignable-role hierarchy root.
CONTRACT: Provide stable branch for user-assignable role classes.
INVARIANTS: ALIVE role mode and inheritance boundary for application roles.
AI-CORE-END

See ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from abc import ABC

from action_machine.auth.base_role import BaseRole
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ApplicationRole(BaseRole, ABC):
    """
    Abstract root of all roles allowed in ``UserInfo.roles``.

    AI-CORE-BEGIN
    ROLE: Role taxonomy anchor for application-level identities.
    CONTRACT: Concrete user roles inherit from this class.
    INVARIANTS: Abstract class with ALIVE role mode.
    AI-CORE-END
    """

    name = "__application_root__"
    description = "Intermediate root for application roles assigned to authenticated users."
