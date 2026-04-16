# src/maxitor/roles/editor.py
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from maxitor.roles.viewer import TestViewerRole


@role_mode(RoleMode.ALIVE)
class TestEditorRole(TestViewerRole):
    name = "test_editor"
    description = "Editor test role (implies viewer)"
