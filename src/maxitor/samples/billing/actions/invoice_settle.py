# src/maxitor/samples/billing/actions/invoice_settle.py
"""Полная поверхность декораторов в домене billing (аналог checkout в store)."""

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
from action_machine.intents.context_requires.context_requires_decorator import context_requires
from action_machine.intents.depends import depends
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.intents.sensitive import sensitive
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.resources import BillingReadReplica, BillingWarehouse
from maxitor.samples.billing.resources.ledger_archive import (
    LedgerArchiveService,
    LedgerArchiveServiceResource,
)
from maxitor.samples.billing.resources.payment_gateway import (
    PaymentGateway,
    PaymentGatewayResource,
)
from maxitor.samples.billing.resources.tax_quote import (
    TaxQuoteService,
    TaxQuoteServiceResource,
)
from maxitor.samples.roles import EditorRole


@meta(description="Settle invoice with full graph facets (billing demo)", domain=BillingDomain)
@check_roles(EditorRole)
@depends(
    PaymentGatewayResource,
    factory=lambda: PaymentGatewayResource(PaymentGateway()),
    description="Card capture",
)
@depends(
    LedgerArchiveServiceResource,
    factory=lambda: LedgerArchiveServiceResource(LedgerArchiveService()),
    description="Ledger append",
)
@depends(
    TaxQuoteServiceResource,
    factory=lambda: TaxQuoteServiceResource(TaxQuoteService()),
    description="Tax rate lookup",
)
@connection(BillingWarehouse, key="warehouse", description="Billing warehouse")
@connection(BillingReadReplica, key="replica", description="Read replica")
class InvoiceSettleAction(BaseAction["InvoiceSettleAction.Params", "InvoiceSettleAction.Result"]):
    class Params(BaseParams):
        invoice_id: str = Field(description="Invoice id")
        gross_cents: int = Field(description="Gross amount in cents", gt=0)

        @property
        @sensitive(True, max_chars=4, char="*", max_percent=40)
        def client_secret_hint(self) -> str:
            return "sec-BILLING-DEMO"

    class Result(BaseResult):
        settlement_id: str = Field(description="Settlement id")
        capture_txn: str = Field(description="Capture transaction id")
        status: str = Field(description="Status label")

    @regular_aspect("Validate invoice")
    @result_string("validated_invoice", required=True, min_length=1)
    @context_requires(Ctx.User.user_id)
    async def validate_invoice_aspect(
        self,
        params: InvoiceSettleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        return {"validated_invoice": params.invoice_id}

    @regular_aspect("Capture funds")
    @result_string("capture_txn", required=True, not_empty=True)
    @result_float("captured_cents", required=True, min_value=0.0)
    async def capture_aspect(
        self,
        params: InvoiceSettleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentGatewayResource)
        cents = float(params.gross_cents)
        txn = await payment.service.charge(cents / 100.0)
        return {"capture_txn": txn, "captured_cents": cents}

    @compensate("capture_aspect", "Void capture on failure")
    async def capture_compensate(
        self,
        params: InvoiceSettleAction.Params,
        state_before: Any,
        state_after: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> None:
        if state_after is not None:
            payment = box.resolve(PaymentGatewayResource)
            await payment.service.refund(state_after.capture_txn)

    @on_error(ValueError, description="Invoice validation failed")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: InvoiceSettleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: ValueError,
        ctx: Any,
    ) -> InvoiceSettleAction.Result:
        return InvoiceSettleAction.Result(
            settlement_id="ERR",
            capture_txn="NONE",
            status="validation_failed",
        )

    @on_error(Exception, description="Billing fallback")
    async def unexpected_error_on_error(
        self,
        params: InvoiceSettleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> InvoiceSettleAction.Result:
        return InvoiceSettleAction.Result(
            settlement_id="ERR",
            capture_txn="NONE",
            status="internal_error",
        )

    @summary_aspect("Build settlement result")
    async def build_result_summary(
        self,
        params: InvoiceSettleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> InvoiceSettleAction.Result:
        return InvoiceSettleAction.Result(
            settlement_id="STL-BILL-1",
            capture_txn=state.capture_txn,
            status="settled",
        )
