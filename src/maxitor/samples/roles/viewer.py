# src/maxitor/samples/roles/viewer.py
from abc import ABC

from action_machine.auth import ApplicationRole
from action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ViewerRole(ApplicationRole, ABC):
    name = "sample_viewer"
    description = "Read-only storefront role"
