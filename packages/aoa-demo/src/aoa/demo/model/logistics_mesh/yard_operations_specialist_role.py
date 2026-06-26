# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/yard_operations_specialist_role.py
"""YardOperationsSpecialistRole — yard orchestration vantage above dock floor."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.logistics_mesh.dock_floor_associate_role import DockFloorAssociateRole


@role_mode(RoleMode.ALIVE)
class YardOperationsSpecialistRole(DockFloorAssociateRole, ABC):
    name = "logistics_yard_operations_specialist"
    description = "Coordinates yard moves once gate slots are hinted"
