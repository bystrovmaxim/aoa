# src/maxitor/samples/roles/legacy.py
from action_machine.auth.application_role import ApplicationRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.DEPRECATED)
class DeprecatedRole(ApplicationRole):
    name = "sample_legacy"
    description = "Deprecated role kept for migration demos"
