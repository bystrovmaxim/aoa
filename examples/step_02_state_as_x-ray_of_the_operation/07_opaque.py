"""
# 07_opaque.py — opaque=True: exclude sensitive fields from state x-ray

By default, every field declared with @result_* ends up in OTel Logs as an
aoa.state.<field> attribute. This is the x-ray: visibility into intermediate state.

Sometimes a field must not appear in logs — a payment token, a database connection,
a customer's SSN, a rich domain object you don't want serialised. Mark the checker
with opaque=True and the field is silently excluded from OTel Logs state attributes.

opaque=True does NOT affect:
  - The checker itself — the field is still validated normally.
  - state["field"] — the value is still in state, readable by downstream aspects.
  - OTel Traces — spans are unaffected (they don't carry state).

This example has two fields in the payment step:
  result_string("order_id") — opaque=False (default) → appears in x-ray
  result_string("payment_token", opaque=True)           → absent from x-ray

Run the example and look at the log records printed to console.
The "aoa.aspect.regular.after" record for payment_aspect will contain
  aoa.state.order_id = "ORD-2024-001"
but NOT aoa.state.payment_token — even though the value is present in state
and is used by the summary to build the confirmation message.

Requires:
    pip install "aoa-action-machine[otel]"

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/07_opaque.py
"""

import asyncio

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class PaymentDomain(BaseDomain):
    name = "payment"
    description = "Payment processing domain"


# ---------------------------------------------------------------------------
# Params and Result
# ---------------------------------------------------------------------------

class PaymentParams(BaseParams):
    order_id: str = Field(description="Order identifier")
    card_last4: str = Field(description="Last four digits of the card (for display only)")


class PaymentResult(BaseResult):
    order_id: str = Field(description="Processed order ID")
    masked_token: str = Field(description="Masked payment token for the receipt")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Charge order and store payment token", domain=PaymentDomain)
@check_roles(GuestRole)
class ChargeOrderAction(BaseAction[PaymentParams, PaymentResult]):

    @regular_aspect("Validate order and mint payment token")
    @result_string("order_id", required=True, min_length=3)
    @result_string("payment_token", required=True, opaque=True)  # ← excluded from x-ray
    async def payment_aspect(self, params, state, box, connections):
        # Simulate minting a payment token from a payment gateway.
        # In production this would be a real API call; here we fabricate one.
        token = f"tok_live_{params.card_last4}_{'x' * 16}"
        return {
            "order_id": params.order_id.upper(),
            "payment_token": token,
        }

    @summary_aspect("Build payment receipt")
    async def receipt_summary(self, params, state, box, connections):
        token: str = state["payment_token"]
        masked = token[:8] + "****" + token[-4:]
        return PaymentResult(
            order_id=state["order_id"],
            masked_token=masked,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    lp = LoggerProvider()
    lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter()))

    plugin = OpenTelemetryPlugin(
        logger_provider=lp,
        service_name="payment-service",
    )
    machine = ActionProductMachine(plugins=[plugin])

    print("Running payment — watch the log record for payment_aspect:\n")
    print("  aoa.state.order_id      → will appear  (opaque=False, default)")
    print("  aoa.state.payment_token → will NOT appear (opaque=True)")
    print()

    result = await machine.run(
        Context(),
        ChargeOrderAction(),
        PaymentParams(order_id="ord-2024-001", card_last4="4242"),
    )

    print(f"\nResult: order={result.order_id}, token={result.masked_token}")
    print()
    print("Note: payment_token is still in state (used by receipt_summary)")
    print("      but it never appears in any log attribute.")


asyncio.run(main())
