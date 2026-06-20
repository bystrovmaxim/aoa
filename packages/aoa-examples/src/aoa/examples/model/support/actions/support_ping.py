# packages/aoa-examples/src/aoa/examples/model/support/actions/support_ping.py
"""Baseline support action — target for same-domain ``@depends``."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.examples.model.support.support_domain import SupportDomain

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
_SupportPingSampleAuditJson = JsonSchemaValue.define(
    name="SupportPingSampleAuditJson",
    schema=_SAMPLE_AUDIT_SCHEMA,
)


@meta(description="Support slice ping (dependency target for same-domain @depends)", domain=SupportDomain)
@check_roles(GuestRole)
class SupportPingAction(BaseAction["SupportPingAction.Params", "SupportPingAction.Result"]):
    class Params(BaseParams):
        label: str = Field(default="support", description="Probe label")

    class Result(BaseResult):
        ok: bool = Field(description="Stub ok flag")
        sample_audit: _SupportPingSampleAuditJson = Field(
            description="Sample JSON payload for JsonSchemaValue graph metadata",
        )

    @summary_aspect("Ack")
    async def ack_summary(
        self,
        params: SupportPingAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> SupportPingAction.Result:
        return SupportPingAction.Result(
            ok=True,
            sample_audit={"events": [], "source": "support_ping"},
        )
