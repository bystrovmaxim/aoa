# tests/domain_model/roles.py
"""Shared ``BaseRole`` markers for the test domain (tokens: admin, manager, editor)."""

from action_machine.auth.base_role import BaseRole
from action_machine.auth.role_mode import RoleMode
from action_machine.auth.role_mode_decorator import role_mode


@role_mode(RoleMode.ALIVE)
class AdminRole(BaseRole):
    name = "admin"
    description = "Administrator."
    includes = ()


@role_mode(RoleMode.ALIVE)
class ManagerRole(BaseRole):
    name = "manager"
    description = "Manager."
    includes = ()


@role_mode(RoleMode.ALIVE)
class EditorRole(BaseRole):
    name = "editor"
    description = "Editor."
    includes = ()
