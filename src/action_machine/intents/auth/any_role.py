# src/action_machine/intents/auth/any_role.py
"""
``AnyRole`` engine sentinel role.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent "any assignable role is enough" requirement in ``@check_roles``.
This is an engine sentinel role type, not an application role for user storage.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Used as ``@check_roles(AnyRole)`` requirement marker.
- Must not be stored in ``UserInfo.roles``.
- Sealed via ``__init_subclass__``: subclassing is forbidden.
- Declared with ``@role_mode(RoleMode.ALIVE)`` as active engine sentinel.

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

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Subclassing ``AnyRole`` raises ``TypeError``.
- This role is runtime-policy metadata only, not a business-domain role.

AI-CORE-BEGIN
ROLE: Engine-level role sentinel.
CONTRACT: Express "any real role required" in role-check declarations.
INVARIANTS: sealed class, ALIVE role mode, not assignable to user role set.
AI-CORE-END

See ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from typing import Any, final

from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.auth.system_role import SystemRole


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
