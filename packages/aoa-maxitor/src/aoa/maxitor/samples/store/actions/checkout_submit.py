# packages/aoa-maxitor/src/aoa/maxitor/samples/store/actions/checkout_submit.py
"""Full action: deps, connections, aspects, checkers, compensate, on_error, sensitive on Params."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import sensitive
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.billing.resources.payment_gateway import PaymentGateway, PaymentGatewayResource
from aoa.maxitor.samples.messaging.resources.notification_gateway import NotificationGatewayResource
from aoa.maxitor.samples.roles import EditorRole
from aoa.maxitor.samples.store.dependencies import _shared_notifier
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.resources import StorefrontDatabase, StorefrontSessionCache


@meta(description="Sample checkout with full decorator surface (graph demo)", domain=StoreDomain)
@check_roles(EditorRole)
@depends(
    PaymentGatewayResource,
    factory=lambda: PaymentGatewayResource(PaymentGateway()),
    description="Payment gateway",
)
@depends(
    NotificationGatewayResource,
    factory=lambda: NotificationGatewayResource(_shared_notifier),
    description="Notifier via factory",
)
@connection(StorefrontDatabase, key="db", description="DB connection")
@connection(StorefrontSessionCache, key="cache", description="Cache connection")
class CheckoutSubmitAction(BaseAction["CheckoutSubmitAction.Params", "CheckoutSubmitAction.Result"]):
    class Params(BaseParams):
        customer_id: str = Field(description="Customer reference id")
        amount: float = Field(description="Monetary amount to charge", gt=0)

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
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        return {"validated_customer": params.customer_id}

    @regular_aspect("Charge payment")
    @result_string("txn_id", required=True, not_empty=True)
    @result_float("charged_amount", required=True, min_value=0.0)
    async def charge_aspect(
        self,
        params: CheckoutSubmitAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentGatewayResource)
        txn_id = await payment.service.charge(params.amount)
        return {"txn_id": txn_id, "charged_amount": params.amount}

    @compensate("charge_aspect", "Refund on failure")
    async def charge_compensate(
        self,
        params: CheckoutSubmitAction.Params,
        state_before: Any,
        state_after: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> None:
        if state_after is not None:
            payment = box.resolve(PaymentGatewayResource)
            await payment.service.refund(state_after.txn_id)

    @on_error(ValueError, description="Validation branch")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: CheckoutSubmitAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: ValueError,
        ctx: Any,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(order_id="ERR", txn_id="NONE", status="validation_failed")

    @on_error(Exception, description="Fallback branch")
    async def unexpected_error_on_error(
        self,
        params: CheckoutSubmitAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(order_id="ERR", txn_id="NONE", status="internal_error")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: CheckoutSubmitAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> CheckoutSubmitAction.Result:
        return CheckoutSubmitAction.Result(
            order_id="ORD-SAMPLE-1",
            txn_id=state.txn_id,
            status="created",
        )
