# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/freight_network_director_role.py
"""FreightNetworkDirectorRole — mesh orchestrator for multi-facility waves."""

from __future__ import annotations

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.logistics_mesh.hub_terminal_director_role import HubTerminalDirectorRole


@role_mode(RoleMode.ALIVE)
class FreightNetworkDirectorRole(HubTerminalDirectorRole):
    name = "logistics_freight_network_director"
    description = "Authorises deepest relay + marshalling overlays"
