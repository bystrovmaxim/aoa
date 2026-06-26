# packages/aoa-demo/src/aoa/demo/model/roles/editor.py
from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.roles.viewer import ViewerRole


@role_mode(RoleMode.ALIVE)
class EditorRole(ViewerRole):
    name = "sample_editor"
    description = "Editor role (implies viewer)"
