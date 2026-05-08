# packages/aoa-maxitor/src/aoa/maxitor/samples/roles/legacy.py
from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.DEPRECATED)
class DeprecatedRole(ApplicationRole):
    name = "sample_legacy"
    description = "Deprecated role kept for migration demos"
