# src/maxitor/test_domain/actions/full_graph.py
"""Полное действие: deps, connections, aspects, checkers, compensate, on_error, sensitive на Params."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.checkers.result_float_checker import result_float
from action_machine.intents.checkers.result_string_checker import result_string
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.logging.sensitive_decorator import sensitive
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.connection_decorator import connection
from maxitor.roles import TestEditorRole
from maxitor.test_domain.dependencies import (
    TestNotificationService,
    TestPaymentService,
    _shared_notifier,
)
from maxitor.test_domain.domain import TestDomain
from maxitor.test_domain.resources import TestCacheManager, TestDbManager


class TestFullGraphParams(BaseParams):
    customer_id: str = Field(description="Customer reference id")
    amount: float = Field(description="Monetary amount to charge", gt=0)

    @property
    @sensitive(True, max_chars=3, char="*", max_percent=50)
    def api_token_hint(self) -> str:
        return "tok-SECRET-GRAPH-ONLY"


class TestFullGraphResult(BaseResult):
    order_id: str = Field(description="Synthetic order id")
    txn_id: str = Field(description="Synthetic transaction id")
    status: str = Field(description="Outcome status label")


@meta(description="Synthetic full graph action (decorators only)", domain=TestDomain)
@check_roles(TestEditorRole)
@depends(TestPaymentService, description="Payment stub")
@depends(
    TestNotificationService,
    factory=lambda: _shared_notifier,
    description="Notifier via factory",
)
@connection(TestDbManager, key="db", description="DB connection")
@connection(TestCacheManager, key="cache", description="Cache connection")
class TestFullGraphAction(BaseAction[TestFullGraphParams, TestFullGraphResult]):
    @regular_aspect("Validate payload")
    @result_string("validated_customer", required=True, min_length=1)
    @context_requires(Ctx.User.user_id)
    async def validate_aspect(
        self,
        params: TestFullGraphParams,
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
        params: TestFullGraphParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        payment = box.resolve(TestPaymentService)
        txn_id = await payment.charge(params.amount)
        return {"txn_id": txn_id, "charged_amount": params.amount}

    @compensate("charge_aspect", "Refund on failure")
    async def charge_compensate(
        self,
        params: TestFullGraphParams,
        state_before: Any,
        state_after: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> None:
        if state_after is not None:
            payment = box.resolve(TestPaymentService)
            await payment.refund(state_after.txn_id)

    @on_error(ValueError, description="Validation branch")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: TestFullGraphParams,
        state: Any,
        box: Any,
        connections: Any,
        error: ValueError,
        ctx: Any,
    ) -> TestFullGraphResult:
        return TestFullGraphResult(order_id="ERR", txn_id="NONE", status="validation_failed")

    @on_error(Exception, description="Fallback branch")
    async def unexpected_error_on_error(
        self,
        params: TestFullGraphParams,
        state: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> TestFullGraphResult:
        return TestFullGraphResult(order_id="ERR", txn_id="NONE", status="internal_error")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: TestFullGraphParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> TestFullGraphResult:
        return TestFullGraphResult(
            order_id="ORD-TEST-1",
            txn_id=state.txn_id,
            status="created",
        )
