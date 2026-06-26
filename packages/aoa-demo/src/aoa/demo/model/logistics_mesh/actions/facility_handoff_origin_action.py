# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/actions/facility_handoff_origin_action.py
"""Origin ingest for facility relay mesh — seeds corridor ladder."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.demo.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Facility hand-off origin gate — seeds relay ladder sequencing", domain=LogisticsMeshDomain)
@check_roles(FreightNetworkDirectorRole)
class FacilityHandoffOriginAction(
    BaseAction["FacilityHandoffOriginAction.Params", "FacilityHandoffOriginAction.Result"],
):
    class Params(BaseParams):
        consignment_token: str = Field(default="", description="Synthetic consignment locator")

    class Result(BaseResult):
        accepted: bool = Field(default=False, description="Origin acceptance acknowledgement")

    @summary_aspect("Facility origin ingest")
    async def origin_summary(self, params: Params, state: Any, box: Any, connections: Any) -> Result:
        _ = (params, state, box, connections)
        return self.Result()
