# packages/aoa-demo/src/aoa/demo/model/store/actions/checkout_submit.py
"""Full action: deps, connections, aspects, checkers, compensate, on_error, sensitive on Params."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.context import ContextView, Ctx
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel, sensitive
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.billing.actions.invoice_settle import InvoiceSettleAction
from aoa.demo.model.messaging.actions.publish_transactional import PublishTransactionalOutboxAction
from aoa.demo.model.roles import EditorRole
from aoa.demo.model.store.resources import StorefrontDatabase, StorefrontSessionCache
from aoa.demo.model.store.store_domain import StoreDomain


@meta(description="Sample checkout with full decorator surface (graph demo)", domain=StoreDomain)
@check_roles(EditorRole)
@depends(InvoiceSettleAction, mode=UseCase.include, description="Charge through billing: its gateway is billing's own")
@depends(PublishTransactionalOutboxAction, mode=UseCase.include, description="Notify through messaging: its gateway is messaging's own")
@connection(StorefrontDatabase, key="db", description="DB connection")
@connection(StorefrontSessionCache, key="cache", description="Cache connection")
class CheckoutSubmitAction(BaseAction["CheckoutSubmitAction.Params", "CheckoutSubmitAction.Result"]):
    class Params(BaseParams):
        customer_id: str = Field(description="Customer reference id")
        amount: float = Field(description="Monetary amount to charge", gt=0)
        promo_code: str = Field(default="", description="Promo code the customer typed; empty when there is none")

        @property
        @sensitive(True, max_chars=3, char="*", max_percent=50)
        def api_token_hint(self) -> str:
            return "tok-SECRET-GRAPH-ONLY"

    class Result(BaseResult):
        order_id: str = Field(description="Synthetic order id")
        txn_id: str = Field(description="Synthetic transaction id")
        status: str = Field(description="Outcome status label")

    @regular_aspect("Validate payload")
    @result_string("validated_customer", required=True, min_length=1)
    @context_requires(Ctx.User.user_id)
    async def validate_aspect(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> dict[str, Any]:
        return {"validated_customer": params.customer_id}

    @regular_aspect("Check promo code")
    @result_string("promo_status", required=True, not_empty=True)
    async def promo_aspect(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        return {"promo_status": "applied" if params.promo_code else "none"}

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True, not_empty=True)
    @result_float("charged_amount", required=True, min_value=0.0)
    async def charge_aspect(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        settled = await box.run(
            InvoiceSettleAction,
            InvoiceSettleAction.Params(invoice_id=f"checkout-{params.customer_id}", gross_cents=round(params.amount * 100)),
        )
        return {"txn_id": settled.capture_txn, "charged_amount": params.amount}

    @compensate(charge_aspect, "Refund on failure")
    async def charge_compensate(
        self,
        params: CheckoutSubmitAction.Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        if state_after is not None:
            # The capture belongs to billing, which voids it in its own compensator; the store only records the request.
            await box.info(Channel.business, "refund of {%state.txn_id} requested from billing")

    @on_error(ValueError, description="Validation branch")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        error: ValueError,
        ctx: ContextView,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(order_id="ERR", txn_id="NONE", status="validation_failed")

    @on_error(Exception, description="Fallback branch")
    async def unexpected_error_on_error(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(order_id="ERR", txn_id="NONE", status="internal_error")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CheckoutSubmitAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(
            order_id="ORD-SAMPLE-1",
            txn_id=state.txn_id,  # type: ignore[attr-defined]
            status="created",
        )
