# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/hub_terminal_director_role.py
"""HubTerminalDirectorRole — consolidated hub SLA owner."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.examples.model.logistics_mesh.gate_dispatch_lead_role import GateDispatchLeadRole


@role_mode(RoleMode.ALIVE)
class HubTerminalDirectorRole(GateDispatchLeadRole, ABC):
    name = "logistics_hub_terminal_director"
    description = "Terminal-level SLA sign-off bridging gate + corridor relay"
