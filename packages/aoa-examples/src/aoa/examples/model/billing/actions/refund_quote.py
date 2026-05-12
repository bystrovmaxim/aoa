# packages/aoa-examples/src/aoa/examples/model/billing/actions/refund_quote.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, JsonSchemaValue
from aoa.examples.model.billing.domain import BillingDomain

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
_BillingRefundQuoteSampleAuditJson = JsonSchemaValue.define(
    name="BillingRefundQuoteSampleAuditJson",
    schema=_SAMPLE_AUDIT_SCHEMA,
)


@meta(description="Quote refundable amount (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
class RefundQuoteAction(BaseAction["RefundQuoteAction.Params", "RefundQuoteAction.Result"]):
    class Params(BaseParams):
        capture_txn: str = Field(description="Original capture id")

    class Result(BaseResult):
        quote_cents: int = Field(description="Stub refundable cents", ge=0)
        sample_audit: _BillingRefundQuoteSampleAuditJson = Field(
            description="Sample JSON payload for JsonSchemaValue graph metadata",
        )

    @summary_aspect("Quote")
    async def quote_summary(
        self,
        params: RefundQuoteAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> RefundQuoteAction.Result:
        return RefundQuoteAction.Result(
            quote_cents=len(params.capture_txn) * 10,
            sample_audit={"events": [], "source": "billing_refund_quote"},
        )
