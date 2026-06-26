# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/actions/cross_edge_observability_portico_action.py
"""Corridor portico — includes deepest normaliser, extends edge briefing."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.demo.model.telemetry_pipeline.actions.edge_facility_downlink_brief_action import (
    EdgeFacilityDownlinkBriefAction,
)
from aoa.demo.model.telemetry_pipeline.actions.stream_normalization_pass_three_action import (
    StreamNormalizationPassThreeAction,
)
from aoa.demo.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(
    description="Portico façade composes deterministic ladder tip with facultative edge brief overlays",
    domain=TelemetryPipelineDomain,
)
@check_roles(IncidentObservabilityDirectorRole)
@depends(
    StreamNormalizationPassThreeAction,
    mode=UseCase.include,
    description="deepest deterministic normaliser inlined into portico",
)
@depends(
    EdgeFacilityDownlinkBriefAction,
    mode=UseCase.extend,
    description="edge briefing overlays remain optional overlays",
)
class CrossEdgeObservabilityPorticoAction(
    BaseAction["CrossEdgeObservabilityPorticoAction.Params", "CrossEdgeObservabilityPorticoAction.Result"],
):
    class Params(BaseParams):
        portico_ticket: str = Field(default="", description="Synthetic portico reconcile ticket")

    class Result(BaseResult):
        routed: bool = Field(default=False, description="Composite routing acknowledgement")

    @summary_aspect("Cross-edge observability portico")
    async def portico_summary(self, params: Params, state: Any, box: Any, connections: Any) -> Result:
        _ = (params, state, box, connections)
        await box.run(StreamNormalizationPassThreeAction, StreamNormalizationPassThreeAction.Params())
        return self.Result()
