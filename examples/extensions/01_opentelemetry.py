"""
01_opentelemetry.py — OpenTelemetryPlugin: traces + state x-ray, from the box

The shipped OpenTelemetryPlugin turns every machine.run() into OpenTelemetry
signals — without touching business code. It is an observer (a Plugin), and it
emits TWO independent signals; you pass at least one provider:

  tracer_provider  → Traces: one root span per run + a child span per aspect /
                     @on_error / compensator (timing & structure)
  logger_provider  → Logs:   a "<event>.after" record per step with
                     aoa.state.<field> attributes — the state x-ray

The plugin contains NO export logic — you choose the backend (console, file, or
any of 50+ OTel backends). Here we use in-memory exporters so the run is
deterministic and needs no collector.

Install:  pip install "aoa-action-machine[otel]"

Extension page: ../../docs/extensions/opentelemetry_draft.md
Concept (plugins / state x-ray): ../../docs/tutorials/step-09-plugins_draft.md , step-02

Run:
    uv run python examples/extensions/01_opentelemetry.py
"""

import asyncio

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


class PriceParams(BaseParams):
    amount: float = Field(gt=0, description="Base amount")


class PriceResult(BaseResult):
    total: float = Field(description="Total with tax")


@meta(description="Price an order", domain=ShopDomain)
@check_roles(GuestRole)
class PriceOrderAction(BaseAction[PriceParams, PriceResult]):

    @regular_aspect("Apply tax")
    @result_float("with_tax", required=True, min_value=0)
    async def tax_aspect(self, params, state, box, connections):
        return {"with_tax": round(params.amount * 1.2, 2)}

    @summary_aspect("Build result")
    async def build_summary(self, params, state, box, connections):
        return PriceResult(total=state["with_tax"])


async def main() -> None:
    # User wires the backend; the plugin only emits. In-memory here for determinism.
    spans = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(spans))

    logs = InMemoryLogRecordExporter()
    logger_provider = LoggerProvider()
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(logs))

    plugin = OpenTelemetryPlugin(tracer_provider=tracer_provider, logger_provider=logger_provider)

    machine = ActionProductMachine(plugins=[plugin])
    result = await machine.run(Context(), PriceOrderAction(), PriceParams(amount=100.0))
    print(f"result: total={result.total}\n")

    # Traces — one root span per run + a child span per step:
    print("Spans (timing & structure):")
    for s in spans.get_finished_spans():
        print(f"  {s.name}")

    # Logs — state x-ray: aoa.state.<field> attributes captured after each step:
    print("\nState x-ray (aoa.state.* from log records):")
    for rec in logs.get_finished_logs():
        lr = rec.log_record
        attrs = dict(lr.attributes or {})
        state = {k.removeprefix("aoa.state."): v for k, v in attrs.items() if k.startswith("aoa.state.")}
        if state:
            print(f"  {lr.body}  step={attrs.get('aoa.aspect')}  state={state}")


if __name__ == "__main__":
    asyncio.run(main())
