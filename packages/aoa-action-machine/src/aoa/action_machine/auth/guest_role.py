# packages/aoa-action-machine/src/aoa/action_machine/auth/guest_role.py
"""
``GuestRole`` engine sentinel role.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent "no authentication required" access policy in ``@check_roles``.
This is an engine sentinel role type, not an assignable business role.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(GuestRole)
            |
            v
    role checker bypasses authenticated-role requirement
            |
            v
    action is callable by anonymous and authenticated users
"""

from __future__ import annotations

from typing import Any, final

from aoa.action_machine.auth.system_role import SystemRole
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@final
@role_mode(RoleMode.ALIVE)
class GuestRole(SystemRole):
    """
    AI-CORE-BEGIN
        ROLE: Public-access check-spec marker.
        CONTRACT: Used only in ``@check_roles`` declarations.
        INVARIANTS: non-subclassable policy role; not part of user role sets.
        AI-CORE-END
    """

    name = "engine_guest"
    description = "Engine sentinel: no authentication required for the action."

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(f"Cannot subclass sealed engine role GuestRole (attempt: {cls.__qualname__!r}).")
