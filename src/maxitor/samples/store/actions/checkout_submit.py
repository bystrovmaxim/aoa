# src/maxitor/samples/store/actions/checkout_submit.py
"""Полное действие: deps, connections, aspects, checkers, compensate, on_error, sensitive на Params."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.checkers.result_float_decorator import result_float
from action_machine.intents.checkers.result_string_decorator import result_string
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.depends import depends
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.intents.sensitive import sensitive
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.billing.resources.payment_gateway import (
    PaymentGateway,
    PaymentGatewayResource,
)
from maxitor.samples.messaging.resources.notification_gateway import (
    NotificationGatewayResource,
)
from maxitor.samples.roles import EditorRole
from maxitor.samples.store.dependencies import _shared_notifier
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.resources import StorefrontDatabase, StorefrontSessionCache


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
