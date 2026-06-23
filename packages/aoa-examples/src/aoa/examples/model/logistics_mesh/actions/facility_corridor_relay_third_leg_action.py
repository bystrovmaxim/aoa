# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/actions/facility_corridor_relay_third_leg_action.py
"""Third relay leg — marshalling prelude."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.logistics_mesh.actions.facility_corridor_relay_second_leg_action import (
    FacilityCorridorRelaySecondLegAction,
)

# ``ActionSchemaIntentResolver`` resolves ``BaseAction`` ForwardRefs via this module globals.
# pylint: disable-next=unused-import
from aoa.examples.model.logistics_mesh.actions.facility_handoff_origin_action import (  # noqa: F401
    FacilityHandoffOriginAction,
)
from aoa.examples.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.examples.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Third relay leg — marshalling apron staging", domain=LogisticsMeshDomain)
@check_roles(FreightNetworkDirectorRole)
class FacilityCorridorRelayThirdLegAction(FacilityCorridorRelaySecondLegAction):
    @summary_aspect("Facility relay leg three")
    async def relay_third_summary(
        self,
        params: FacilityCorridorRelaySecondLegAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> FacilityCorridorRelaySecondLegAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
