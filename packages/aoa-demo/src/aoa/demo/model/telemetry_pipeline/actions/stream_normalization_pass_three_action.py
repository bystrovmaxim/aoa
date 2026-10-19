# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/actions/stream_normalization_pass_three_action.py
"""Third pass — deterministic correlator prelude."""

from __future__ import annotations

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

# ``ActionSchemaIntentResolver`` resolves ``BaseAction`` ForwardRefs via this module globals.
# pylint: disable-next=unused-import
from aoa.demo.model.telemetry_pipeline.actions.stream_ingress_anchor_action import (  # noqa: F401
    StreamIngressAnchorAction,
)
from aoa.demo.model.telemetry_pipeline.actions.stream_normalization_pass_two_action import (
    StreamNormalizationPassTwoAction,
)
from aoa.demo.model.telemetry_pipeline.incident_observability_director_role import IncidentObservabilityDirectorRole
from aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain import TelemetryPipelineDomain


@meta(description="Normalisation ladder pass three — correlator-ready projection", domain=TelemetryPipelineDomain)
@check_roles(IncidentObservabilityDirectorRole)
class StreamNormalizationPassThreeAction(StreamNormalizationPassTwoAction):
    @summary_aspect("Normalizer pass three")
    async def pass_three_summary(
        self,
        params: StreamNormalizationPassTwoAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> StreamNormalizationPassTwoAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
