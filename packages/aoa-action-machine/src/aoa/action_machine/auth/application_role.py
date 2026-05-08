# packages/aoa-action-machine/src/aoa/action_machine/auth/application_role.py
"""
``ApplicationRole`` root for assignable business roles.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define a common abstract root for roles that may be assigned to authenticated
users and stored in ``UserInfo.roles``.

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
"""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.graph.exclude_graph_model import exclude_graph_model


@exclude_graph_model
@role_mode(RoleMode.ALIVE)
class ApplicationRole(BaseRole, ABC):
    """
AI-CORE-BEGIN
    ROLE: Role taxonomy anchor for application-level identities.
    CONTRACT: Concrete user roles inherit from this class.
    INVARIANTS: Abstract class with ALIVE role mode.
    AI-CORE-END
"""

    name = "__application_root__"
    description = "Intermediate root for application roles assigned to authenticated users."
