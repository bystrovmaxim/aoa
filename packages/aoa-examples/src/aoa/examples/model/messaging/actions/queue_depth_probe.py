# packages/aoa-examples/src/aoa/examples/model/messaging/actions/queue_depth_probe.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.examples.model.messaging.domain import MessagingDomain

_SAMPLE_AUDIT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        "source": {"type": "string"},
    },
    "required": ["events", "source"],
    "additionalProperties": False,
}
_MessagingQueueDepthSampleAuditJson = JsonSchemaValue.define(
    name="MessagingQueueDepthSampleAuditJson",
    schema=_SAMPLE_AUDIT_SCHEMA,
)


@meta(description="Probe queue depth (messaging sample stub)", domain=MessagingDomain)
@check_roles(NoneRole)
class QueueDepthProbeAction(BaseAction["QueueDepthProbeAction.Params", "QueueDepthProbeAction.Result"]):
    class Params(BaseParams):
        queue_name: str = Field(description="Logical queue name")

    class Result(BaseResult):
        depth: int = Field(description="Stub depth", ge=0)
        sample_audit: _MessagingQueueDepthSampleAuditJson = Field(
            description="Sample JSON payload for JsonSchemaValue graph metadata",
        )

    @summary_aspect("Probe")
    async def probe_summary(
        self,
        params: QueueDepthProbeAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> QueueDepthProbeAction.Result:
        return QueueDepthProbeAction.Result(
            depth=len(params.queue_name) % 5,
            sample_audit={"events": [], "source": "messaging_queue_depth_probe"},
        )
