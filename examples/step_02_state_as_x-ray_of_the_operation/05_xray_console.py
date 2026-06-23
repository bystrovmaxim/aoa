"""
# 05_xray_console.py — State x-ray via OpenTelemetry (console output)

OpenTelemetryPlugin wires into ActionMachine as a plugin.
No changes to Action code — all observability is in the machine setup.

Two signals, both optional, can be combined:

  tracer_provider → OTel Traces
    One root span per machine.run().
    One child span per @regular_aspect, @on_error, and compensator.
    Span name = aspect method name. Duration and status recorded automatically.

  logger_provider → OTel Logs (state x-ray)
    One log record per lifecycle event.
    After @regular_aspect: log body "aoa.aspect.regular.after" carries
    aoa.state.<field> attributes — one per field in the returned dict.
    This is the x-ray: you see the exact state after every step.

This example uses ConsoleSpanExporter and ConsoleLogExporter — both write
to stdout so you can see spans and logs side by side without any backend.

Requires:
    pip install aoa-otel

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.py
"""

import asyncio

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_int, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.otel import OpenTelemetryPlugin

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class CheckoutDomain(BaseDomain):
    name = "checkout"
    description = "E-commerce checkout pipeline"


# ---------------------------------------------------------------------------
# Params and Result
# ---------------------------------------------------------------------------

class CheckoutParams(BaseParams):
    sku: str = Field(description="Product SKU")
    quantity: int = Field(description="Number of units")
    unit_price: float = Field(description="Price per unit in USD")


class CheckoutResult(BaseResult):
    sku: str = Field(description="Validated SKU")
    total: float = Field(description="Order total in USD")
    confirmation: str = Field(description="Human-readable confirmation message")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Three-step checkout: validate → enrich → confirm", domain=CheckoutDomain)
@check_roles(GuestRole)
class CheckoutAction(BaseAction[CheckoutParams, CheckoutResult]):

    @regular_aspect("Step 1: Validate SKU and quantity")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1, max_value=500)
    async def validate_aspect(self, params, state, box, connections):
        # After this aspect, state = {"sku": ..., "quantity": ...}
        # x-ray will log: aoa.state.sku, aoa.state.quantity
        return {
            "sku": params.sku.strip().upper(),
            "quantity": params.quantity,
        }

    @regular_aspect("Step 2: Calculate total")
    @result_string("sku", required=True)
    @result_int("quantity", required=True)
    @result_float("total", required=True, min_value=0.01)
    async def enrich_aspect(self, params, state, box, connections):
        # After this aspect, state = {"sku": ..., "quantity": ..., "total": ...}
        # x-ray will log: aoa.state.sku, aoa.state.quantity, aoa.state.total
        total = round(state["quantity"] * params.unit_price, 2)
        return {
            "sku": state["sku"],
            "quantity": state["quantity"],
            "total": total,
        }

    @summary_aspect("Step 3: Confirm order")
    async def confirm_summary(self, params, state, box, connections):
        return CheckoutResult(
            sku=state["sku"],
            total=state["total"],
            confirmation=f"Order confirmed: {state['quantity']}x {state['sku']} = ${state['total']}",
        )


# ---------------------------------------------------------------------------
# OTel setup
# ---------------------------------------------------------------------------

def build_tracer_provider() -> TracerProvider:
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    return tp


def build_logger_provider() -> LoggerProvider:
    lp = LoggerProvider()
    lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter()))
    return lp


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    plugin = OpenTelemetryPlugin(
        tracer_provider=build_tracer_provider(),
        logger_provider=build_logger_provider(),
        service_name="checkout-service",
    )
    machine = ActionProductMachine(plugins=[plugin])

    print("Running checkout — watch for OTel spans and x-ray logs below:\n")
    result = await machine.run(
        Context(),
        CheckoutAction(),
        CheckoutParams(sku=" widget-42 ", quantity=3, unit_price=19.99),
    )
    print(f"\nFinal result: {result.confirmation}")


asyncio.run(main())
