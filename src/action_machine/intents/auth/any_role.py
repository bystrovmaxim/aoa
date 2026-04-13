# src/action_machine/intents/auth/any_role.py
"""
``AnyRole`` — сентинел движка: нужна хотя бы одна неслужебная роль пользователя.

См. ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from typing import Any, final

from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.auth.system_role import SystemRole


@final
@role_mode(RoleMode.ALIVE)
class AnyRole(SystemRole):
    """
    Требуется хотя бы одна роль пользователя (не ``SILENCED``).

    Использовать ``@check_roles(AnyRole)``. Не помещать ``AnyRole`` в ``UserInfo.roles``.
    """

    name = "engine_any"
    description = "Engine sentinel: at least one assignable role required."

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(
            f"Cannot subclass sealed engine role AnyRole (attempt: {cls.__qualname__!r})."
        )
