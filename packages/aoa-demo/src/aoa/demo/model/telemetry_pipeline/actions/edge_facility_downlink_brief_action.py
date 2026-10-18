# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/actions/edge_facility_downlink_brief_action.py
"""Edge briefing slice — optional correlate extension façade."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Edge/downlink condensed brief for responders", domain=TelemetryPipelineDomain)
@check_roles(IncidentObservabilityDirectorRole)
class EdgeFacilityDownlinkBriefAction(
    BaseAction["EdgeFacilityDownlinkBriefAction.Params", "EdgeFacilityDownlinkBriefAction.Result"],
):
    class Params(BaseParams):
        briefing_handle: str = Field(default="", description="Synthetic edge deck locator")

    class Result(BaseResult):
        synthesized: bool = Field(default=False, description="Brief synthesis acknowledgement")

    @summary_aspect("Edge downlink briefing")
    async def brief_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: dict[str, BaseResource]) -> Result:
        _ = (params, state, box, connections)
        return self.Result()
