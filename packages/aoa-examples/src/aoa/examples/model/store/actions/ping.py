# packages/aoa-examples/src/aoa/examples/model/store/actions/ping.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.examples.model.store.store_domain import StoreDomain

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
_StoreOpsPingSampleAuditJson = JsonSchemaValue.define(
    name="StoreOpsPingSampleAuditJson",
    schema=_SAMPLE_AUDIT_SCHEMA,
)


@meta(description="Health ping for the storefront slice", domain=StoreDomain)
@check_roles(GuestRole)
class OpsPingAction(BaseAction["OpsPingAction.Params", "OpsPingAction.Result"]):
    class Params(BaseParams):
        ping: str = Field(default="ping", description="Ping payload")

    class Result(BaseResult):
        message: str = Field(description="Pong message")
        sample_audit: _StoreOpsPingSampleAuditJson = Field(
            description="Sample JSON payload for JsonSchemaValue graph metadata",
        )

    @summary_aspect("Pong")
    @context_requires(Ctx.Request.trace_id)
    async def pong_summary(
        self,
        params: OpsPingAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        _ctx: object,
    ) -> OpsPingAction.Result:
        return OpsPingAction.Result(
            message="pong",
            sample_audit={"events": [], "source": "store_ops_ping"},
        )
