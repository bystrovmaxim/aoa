# src/maxitor/samples/roles/editor.py
from action_machine.intents.check_roles import RoleMode, role_mode
from maxitor.samples.roles.viewer import ViewerRole


@role_mode(RoleMode.ALIVE)
class EditorRole(ViewerRole):
    name = "sample_editor"
    description = "Editor role (implies viewer)"
