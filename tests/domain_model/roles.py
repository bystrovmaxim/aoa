# tests/domain_model/roles.py
"""Shared ``ApplicationRole`` markers for the test domain."""

from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.role_mode import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class AdminRole(ApplicationRole):
    name = "admin"
    description = "Administrator."


@role_mode(RoleMode.ALIVE)
class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Manager."


@role_mode(RoleMode.ALIVE)
class EditorRole(ApplicationRole):
    name = "editor"
    description = "Editor."


@role_mode(RoleMode.ALIVE)
class UserRole(ApplicationRole):
    name = "user"
    description = "Standard user."


@role_mode(RoleMode.ALIVE)
class SpyRole(ApplicationRole):
    name = "spy"
    description = "Spy (test)."


@role_mode(RoleMode.ALIVE)
class AgentRole(ApplicationRole):
    name = "agent"
    description = "Agent (test)."


@role_mode(RoleMode.ALIVE)
class ServiceRole(ApplicationRole):
    name = "service"
    description = "Service principal (test)."


@role_mode(RoleMode.ALIVE)
class GuestRole(ApplicationRole):
    name = "guest"
    description = "Guest (test)."
