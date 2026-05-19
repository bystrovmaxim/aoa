# packages/aoa-examples/src/aoa/examples/model/telemetry_pipeline/actions/stream_normalization_pass_one_action.py
"""First deterministic normaliser pass anchored on ingestion."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.telemetry_pipeline.actions.stream_ingress_anchor_action import StreamIngressAnchorAction
from aoa.examples.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.examples.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Normalisation ladder pass one — deterministic taxonomy projection", domain=TelemetryPipelineDomain)
@check_roles(IncidentObservabilityDirectorRole)
class StreamNormalizationPassOneAction(StreamIngressAnchorAction):
    @summary_aspect("Normalizer pass one")
    async def pass_one_summary(
        self,
        params: StreamIngressAnchorAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> StreamIngressAnchorAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
