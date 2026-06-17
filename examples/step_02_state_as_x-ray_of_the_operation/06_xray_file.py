"""
# 06_xray_file.py — State x-ray to files + watch_events filtering

Two extensions from 05_xray_console.py:

1. WRITE TO FILES instead of stdout.
   ConsoleSpanExporter and ConsoleLogExporter both accept an `out` parameter —
   any file-like object. Pass an open file handle to redirect output.
   After the run: traces.txt and logs.txt contain the raw OTel output.

2. watch_events — filter which events reach the plugin.
   By default, OpenTelemetryPlugin receives every event. watch_events limits it
   to an explicit set of event types. This is useful when you only care about
   specific signals — for example, the state snapshot after each regular step,
   plus the final finish event, without all the Before*/Start noise.

   This example sets up TWO plugin instances on the same machine:
   - plugin_traces: full tracing (all events), writes to traces.txt
   - plugin_logs:   only AfterRegularAspectEvent + GlobalFinishEvent, writes to logs.txt

   The action code (CheckoutAction from 05_xray_console.py) is reused as-is.

After running, open traces.txt and logs.txt to compare:
  traces.txt — all spans (full execution picture)
  logs.txt   — only after-step and finish records (focused state x-ray)

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.py
"""

import asyncio
import os

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_int, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.core.events import AfterRegularAspectEvent, GlobalFinishEvent
from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ---------------------------------------------------------------------------
# Domain, Params, Result  (same business logic as 05_xray_console.py)
# ---------------------------------------------------------------------------

class CheckoutDomain(BaseDomain):
    name = "checkout"
    description = "E-commerce checkout pipeline"


class CheckoutParams(BaseParams):
    sku: str = Field(description="Product SKU")
    quantity: int = Field(description="Number of units")
    unit_price: float = Field(description="Price per unit in USD")


class CheckoutResult(BaseResult):
    sku: str = Field(description="Validated SKU")
    total: float = Field(description="Order total in USD")
    confirmation: str = Field(description="Human-readable confirmation message")


@meta(description="Three-step checkout: validate → enrich → confirm", domain=CheckoutDomain)
@check_roles(NoneRole)
class CheckoutAction(BaseAction[CheckoutParams, CheckoutResult]):

    @regular_aspect("Step 1: Validate SKU and quantity")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1, max_value=500)
    async def validate_aspect(self, params, state, box, connections):
        return {"sku": params.sku.strip().upper(), "quantity": params.quantity}

    @regular_aspect("Step 2: Calculate total")
    @result_string("sku", required=True)
    @result_int("quantity", required=True)
    @result_float("total", required=True, min_value=0.01)
    async def enrich_aspect(self, params, state, box, connections):
        return {
            "sku": state["sku"],
            "quantity": state["quantity"],
            "total": round(state["quantity"] * params.unit_price, 2),
        }

    @summary_aspect("Step 3: Confirm order")
    async def confirm_summary(self, params, state, box, connections):
        return CheckoutResult(
            sku=state["sku"],
            total=state["total"],
            confirmation=f"Order confirmed: {state['quantity']}x {state['sku']} = ${state['total']}",
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

OUTPUT_DIR = os.path.dirname(__file__)


async def main() -> None:
    traces_path = os.path.join(OUTPUT_DIR, "traces.txt")
    logs_path = os.path.join(OUTPUT_DIR, "logs.txt")

    with open(traces_path, "w") as traces_file, open(logs_path, "w") as logs_file:

        # Plugin 1: full tracing — all events, spans to traces.txt
        tp = TracerProvider()
        tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=traces_file)))
        plugin_traces = OpenTelemetryPlugin(
            tracer_provider=tp,
            service_name="checkout-service",
        )

        # Plugin 2: focused logs — only state x-ray after each regular step and finish
        lp = LoggerProvider()
        lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=logs_file)))
        plugin_logs = OpenTelemetryPlugin(
            logger_provider=lp,
            service_name="checkout-service",
            watch_events=frozenset({AfterRegularAspectEvent, GlobalFinishEvent}),
        )

        machine = ActionProductMachine(plugins=[plugin_traces, plugin_logs])

        result = await machine.run(
            Context(),
            CheckoutAction(),
            CheckoutParams(sku=" widget-42 ", quantity=3, unit_price=19.99),
        )

    print(f"Result: {result.confirmation}")
    print()
    print(f"Traces written to: {traces_path}")
    print(f"  (root span + 2 child spans — one per @regular_aspect)")
    print()
    print(f"Logs written to:   {logs_path}")
    print(f"  (only AfterRegularAspectEvent + GlobalFinishEvent)")
    print(f"  (Before*/Start events filtered out by watch_events)")


asyncio.run(main())
