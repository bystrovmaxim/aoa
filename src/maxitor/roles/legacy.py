# src/maxitor/roles/legacy.py
from action_machine.intents.auth.application_role import ApplicationRole
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.DEPRECATED)
class TestLegacyRole(ApplicationRole):
    name = "test_legacy"
    description = "Deprecated test role"
