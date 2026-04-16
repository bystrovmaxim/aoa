# src/maxitor/roles/viewer.py
from abc import ABC

from action_machine.intents.auth.application_role import ApplicationRole
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class TestViewerRole(ApplicationRole, ABC):
    name = "test_viewer"
    description = "Read-only test role"
