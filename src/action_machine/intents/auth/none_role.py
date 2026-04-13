# src/action_machine/intents/auth/none_role.py
"""
``NoneRole`` — сентинел движка: действие без требования аутентификации.

См. ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from typing import Any, final

from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.auth.system_role import SystemRole


@final
@role_mode(RoleMode.ALIVE)
class NoneRole(SystemRole):
    """
    Действие доступно всем, включая анонимных пользователей.

    Использовать ``@check_roles(NoneRole)``. Не помещать ``NoneRole`` в ``UserInfo.roles``.
    """

    name = "engine_none"
    description = "Engine sentinel: no authentication required for the action."

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError(
            f"Cannot subclass sealed engine role NoneRole (attempt: {cls.__qualname__!r})."
        )
