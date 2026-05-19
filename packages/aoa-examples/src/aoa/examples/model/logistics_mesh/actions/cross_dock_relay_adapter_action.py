# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/actions/cross_dock_relay_adapter_action.py
"""Cross-dock relay adapter façade used as facultative orchestration overlay."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.logistics_mesh.freight_network_director_role import FreightNetworkDirectorRole
from aoa.examples.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@meta(description="Adaptive cross-dock adapter harmonising berth vs conveyor cadence", domain=LogisticsMeshDomain)
@check_roles(FreightNetworkDirectorRole)
class CrossDockRelayAdapterAction(
    BaseAction["CrossDockRelayAdapterAction.Params", "CrossDockRelayAdapterAction.Result"],
):
    class Params(BaseParams):
        adapter_lane: str = Field(default="", description="Synthetic conveyor / dray adaptor handle")

    class Result(BaseResult):
        patched: bool = Field(default=False, description="Adaptor patch acknowledgement")

    @summary_aspect("Cross-dock relay adapter")
    async def adapter_summary(self, params: Params, state: Any, box: Any, connections: Any) -> Result:
        _ = (params, state, box, connections)
        return self.Result()
