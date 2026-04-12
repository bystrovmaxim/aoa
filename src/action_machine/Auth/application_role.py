# src/action_machine/auth/application_role.py
"""
``ApplicationRole`` — корень ролей, которые можно назначать пользователю.

См. ``docs/architecture/role-hierarchy.md``.
"""

from __future__ import annotations

from abc import ABC

from action_machine.auth.base_role import BaseRole
from action_machine.auth.role_mode import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ApplicationRole(BaseRole, ABC):
    """
    Корень всех ролей, допустимых в ``UserInfo.roles``.

    Прикладные роли наследуют от этого класса, а не напрямую от ``BaseRole``.
    """

    name = "__application_root__"
    description = "Intermediate root for application roles assigned to authenticated users."
