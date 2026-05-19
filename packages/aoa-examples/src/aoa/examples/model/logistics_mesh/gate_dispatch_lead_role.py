# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/gate_dispatch_lead_role.py
"""GateDispatchLeadRole — gate timetable + berth arbitration."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.examples.model.logistics_mesh.yard_operations_specialist_role import YardOperationsSpecialistRole


@role_mode(RoleMode.ALIVE)
class GateDispatchLeadRole(YardOperationsSpecialistRole, ABC):
    name = "logistics_gate_dispatch_lead"
    description = "Owns berth allocation windows feeding relay legs"
