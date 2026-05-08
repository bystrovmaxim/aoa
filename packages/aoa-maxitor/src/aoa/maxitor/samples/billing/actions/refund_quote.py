# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/actions/refund_quote.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.billing.domain import BillingDomain


@meta(description="Quote refundable amount (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
class RefundQuoteAction(BaseAction["RefundQuoteAction.Params", "RefundQuoteAction.Result"]):
    class Params(BaseParams):
        capture_txn: str = Field(description="Original capture id")

    class Result(BaseResult):
        quote_cents: int = Field(description="Stub refundable cents", ge=0)

    @summary_aspect("Quote")
    async def quote_summary(
        self,
        params: RefundQuoteAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> RefundQuoteAction.Result:
        return RefundQuoteAction.Result(quote_cents=len(params.capture_txn) * 10)
