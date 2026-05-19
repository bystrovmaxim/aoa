# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/actions/marshalling_yard_facility_concourse_action.py
"""Marshalling concourse orchestrator — inl deepest relay leg, optional adapter overlay."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.logistics_mesh.actions.cross_dock_relay_adapter_action import CrossDockRelayAdapterAction
from aoa.examples.model.logistics_mesh.actions.facility_corridor_relay_third_leg_action import (
    FacilityCorridorRelayThirdLegAction,
)
from aoa.examples.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.examples.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(
    description="Marshalling concourse weaves deepest relay choreography with adaptor overlays",
    domain=LogisticsMeshDomain,
)
@check_roles(FreightNetworkDirectorRole)
@depends(
    FacilityCorridorRelayThirdLegAction,
    mode=UseCase.include,
    description="deepest deterministic relay leg inlined into concourse",
)
@depends(
    CrossDockRelayAdapterAction,
    mode=UseCase.extend,
    description="adaptor overlays extend concourse choreography",
)
class MarshallingYardFacilityConcourseAction(
    BaseAction["MarshallingYardFacilityConcourseAction.Params", "MarshallingYardFacilityConcourseAction.Result"],
):
    class Params(BaseParams):
        orchestration_wave: str = Field(default="", description="Synthetic orchestration wave id")

    class Result(BaseResult):
        synced: bool = Field(default=False, description="Orchestration sync acknowledgement")

    @summary_aspect("Marshalling concourse weave")
    async def concourse_summary(self, params: Params, state: Any, box: Any, connections: Any) -> Result:
        _ = (params, state, box, connections)
        await box.run(
            FacilityCorridorRelayThirdLegAction,
            FacilityCorridorRelayThirdLegAction.Params(),
        )
        return self.Result()
