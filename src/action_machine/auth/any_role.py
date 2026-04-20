# src/action_machine/auth/any_role.py
"""
``AnyRole`` engine sentinel role.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent "any assignable role is enough" requirement in ``@check_roles``.
This is an engine sentinel role type, not an application role for user storage.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AnyRole)
            |
            v
    role checker evaluates UserInfo.roles
            |
            v
    pass when at least one assignable role exists
"""

from __future__ import annotations

from typing import Any, final

from action_machine.auth.system_role import SystemRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@final
@role_mode(RoleMode.ALIVE)
class AnyRole(SystemRole):
    """
    Sentinel role requiring at least one assignable user role.

    AI-CORE-BEGIN
    ROLE: Check-spec marker for permissive role requirement.
    CONTRACT: Used only in ``@check_roles`` declarations.
    INVARIANTS: non-instantiable policy role; not stored in user role payload.
    AI-CORE-END
    """

    name = "engine_any"
    description = "Engine sentinel: at least one assignable role required."

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(
            f"Cannot subclass sealed engine role AnyRole (attempt: {cls.__qualname__!r})."
        )
