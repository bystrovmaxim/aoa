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
"""

from __future__ import annotations

from abc import ABC

from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class SystemRole(BaseRole, ABC):
    """
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
