# packages/aoa-examples/src/aoa/examples/model/roles/viewer.py
from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ViewerRole(ApplicationRole, ABC):
    name = "sample_viewer"
    description = "Read-only storefront role"
