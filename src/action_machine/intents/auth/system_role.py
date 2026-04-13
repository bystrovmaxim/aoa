# src/action_machine/intents/auth/system_role.py
"""
``SystemRole`` — корень служебных ролей движка (не для ``UserInfo.roles``).

См. дерево в ``docs/architecture/role-hierarchy.md`` и пакет ``action_machine.intents.auth``.
"""

from __future__ import annotations

from abc import ABC

from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class SystemRole(BaseRole, ABC):
    """
    Корень типов ролей только для спецификации ``@check_roles``.

    Не перечислять в ``UserInfo.roles`` — там только подклассы ``ApplicationRole``.
    """

    name = "__system_root__"
    description = (
        "Intermediate root for engine sentinel roles (not assignable to UserInfo.roles)."
    )
