# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/actions/facility_corridor_relay_first_leg_action.py
"""First corridor relay leg — specialises origin ingest."""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.logistics_mesh.actions.facility_handoff_origin_action import FacilityHandoffOriginAction
from aoa.demo.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="First relay leg — berth + gate handshake", domain=LogisticsMeshDomain)
@check_roles(FreightNetworkDirectorRole)
class FacilityCorridorRelayFirstLegAction(FacilityHandoffOriginAction):
    @summary_aspect("Facility relay leg one")
    async def relay_first_summary(
        self,
        params: FacilityHandoffOriginAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> FacilityHandoffOriginAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
