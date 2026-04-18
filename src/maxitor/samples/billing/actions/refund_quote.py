# src/maxitor/samples/billing/actions/refund_quote.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.billing.domain import BillingDomain


class RefundQuoteParams(BaseParams):
    capture_txn: str = Field(description="Original capture id")


class RefundQuoteResult(BaseResult):
    quote_cents: int = Field(description="Stub refundable cents", ge=0)


@meta(description="Quote refundable amount (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
class RefundQuoteAction(BaseAction[RefundQuoteParams, RefundQuoteResult]):
    @summary_aspect("Quote")
    async def quote_summary(
        self,
        params: RefundQuoteParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> RefundQuoteResult:
        return RefundQuoteResult(quote_cents=len(params.capture_txn) * 10)
