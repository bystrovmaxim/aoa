# packages/aoa-examples/src/aoa/examples/model/telemetry_pipeline/actions/stream_normalization_pass_two_action.py
"""Second normaliser specialising pass-one posture."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta

# ``ActionSchemaIntentResolver`` resolves ``BaseAction`` ForwardRefs via this module globals.
# pylint: disable-next=unused-import
from aoa.examples.model.telemetry_pipeline.actions.stream_ingress_anchor_action import (  # noqa: F401
    StreamIngressAnchorAction,
)
from aoa.examples.model.telemetry_pipeline.actions.stream_normalization_pass_one_action import (
    StreamNormalizationPassOneAction,
)
from aoa.examples.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.examples.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Normalisation ladder pass two — cardinality guards", domain=TelemetryPipelineDomain)
@check_roles(IncidentObservabilityDirectorRole)
class StreamNormalizationPassTwoAction(StreamNormalizationPassOneAction):
    @summary_aspect("Normalizer pass two")
    async def pass_two_summary(
        self,
        params: StreamNormalizationPassOneAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> StreamNormalizationPassOneAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
