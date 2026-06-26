# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/dock_floor_associate_role.py
"""DockFloorAssociateRole — floor executor for provisional freight placement."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class DockFloorAssociateRole(ApplicationRole, ABC):
    name = "logistics_dock_floor_associate"
    description = "Executes provisional dock placements under supervision"
