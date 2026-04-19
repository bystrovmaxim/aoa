# src/maxitor/samples/billing/actions/refund_quote.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth.none_role import NoneRole
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.billing.domain import BillingDomain


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
