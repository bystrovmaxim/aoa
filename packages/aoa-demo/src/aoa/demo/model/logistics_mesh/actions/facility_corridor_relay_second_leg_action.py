# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/actions/facility_corridor_relay_second_leg_action.py
"""Second relay leg chaining deeper into yard mesh."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.demo.model.logistics_mesh.actions.facility_corridor_relay_first_leg_action import (
    FacilityCorridorRelayFirstLegAction,
)

# ``ActionSchemaIntentResolver`` resolves ``BaseAction`` ForwardRefs via this module globals.
# pylint: disable-next=unused-import
from aoa.demo.model.logistics_mesh.actions.facility_handoff_origin_action import (  # noqa: F401
    FacilityHandoffOriginAction,
)
from aoa.demo.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Second relay leg — cross-aisle marshal buffer", domain=LogisticsMeshDomain)
@check_roles(FreightNetworkDirectorRole)
class FacilityCorridorRelaySecondLegAction(FacilityCorridorRelayFirstLegAction):
    @summary_aspect("Facility relay leg two")
    async def relay_second_summary(
        self,
        params: FacilityCorridorRelayFirstLegAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> FacilityCorridorRelayFirstLegAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
