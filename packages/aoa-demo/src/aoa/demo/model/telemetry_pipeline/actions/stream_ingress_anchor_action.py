# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/actions/stream_ingress_anchor_action.py
"""Anchor ingest posture for deterministic streaming ladder."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.demo.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Ingress anchor binding edge batches into streaming ladder contract", domain=TelemetryPipelineDomain)
@check_roles(IncidentObservabilityDirectorRole)
class StreamIngressAnchorAction(
    BaseAction["StreamIngressAnchorAction.Params", "StreamIngressAnchorAction.Result"],
):
    class Params(BaseParams):
        stream_seed: str = Field(default="", description="Opaque edge batch discriminator")

    class Result(BaseResult):
        anchored: bool = Field(default=True, description="Ingress anchor acknowledged")

    @summary_aspect("Stream ingress anchor")
    async def anchor_summary(self, params: Params, state: Any, box: Any, connections: Any) -> Result:
        _ = (params, state, box, connections)
        return self.Result()
