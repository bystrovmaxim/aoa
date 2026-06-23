# packages/aoa-examples/src/aoa/examples/model/store/ocel_export.py
"""
Store OCEL export — machine wiring and batch trace execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``build_store_ocel_machine`` shares one ``StoreOcelStoreResource`` between
``@connection`` and ``OcelPlugin``. ``run_store_ocel_trace_batch`` opens the
store once, runs mixed storefront scenarios, then persists JSON on ``close()``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple, cast

from aoa.action_machine.context import Context, RequestInfo
from aoa.action_machine.model import BaseAction, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.examples.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)
from aoa.examples.model.store.actions.store_ocel_traces import (
    STORE_OCEL_CONNECTION_KEY,
    PublishOrderCreatedOcelAction,
    PublishOrderLinePickedOcelAction,
    PublishOrderPaymentOcelAction,
    PublishOrderReturnOcelAction,
    PublishOrderShippedOcelAction,
    StoreOcelTraceParams,
    StoreOcelTraceResult,
)
from aoa.examples.model.store.resources.ocel_store import StoreOcelStoreResource
from aoa.ocel import OcelPlugin

type StoreOcelActionClass = type[BaseAction[StoreOcelTraceParams, BaseResult]]

STORE_OCEL_SCENARIO_STANDARD = cast(
    "tuple[StoreOcelActionClass, ...]",
    (
        PublishOrderCreatedOcelAction,
        PublishOrderPaymentOcelAction,
        PublishOrderLinePickedOcelAction,
        PublishOrderShippedOcelAction,
    ),
)
STORE_OCEL_SCENARIO_EXPRESS = cast(
    "tuple[StoreOcelActionClass, ...]",
    (
        PublishOrderCreatedOcelAction,
        PublishOrderLinePickedOcelAction,
        PublishOrderShippedOcelAction,
    ),
)
STORE_OCEL_SCENARIO_WITH_RETURN = cast(
    "tuple[StoreOcelActionClass, ...]",
    (
        PublishOrderCreatedOcelAction,
        PublishOrderPaymentOcelAction,
        PublishOrderLinePickedOcelAction,
        PublishOrderShippedOcelAction,
        PublishOrderReturnOcelAction,
    ),
)

STORE_OCEL_SCENARIOS: dict[str, tuple[StoreOcelActionClass, ...]] = {
    "standard": STORE_OCEL_SCENARIO_STANDARD,
    "express": STORE_OCEL_SCENARIO_EXPRESS,
    "with_return": STORE_OCEL_SCENARIO_WITH_RETURN,
}

STORE_OCEL_LIFECYCLE_ACTIONS = STORE_OCEL_SCENARIO_STANDARD

__all__ = [
    "STORE_OCEL_CONNECTION_KEY",
    "STORE_OCEL_LIFECYCLE_ACTIONS",
    "STORE_OCEL_SCENARIOS",
    "StoreOcelActionClass",
    "StoreOcelTracePlanEntry",
    "build_store_ocel_machine",
    "iter_store_ocel_trace_plan",
    "run_store_ocel_trace_batch",
]


class StoreOcelTracePlanEntry(NamedTuple):
    """One scheduled OCEL export action in a mixed batch."""

    action_cls: StoreOcelActionClass
    order_index: int
    scenario: str


def iter_store_ocel_trace_plan(event_count: int) -> Iterator[StoreOcelTracePlanEntry]:
    """Yield mixed scenarios (standard / express / with_return) until ``event_count`` events."""
    if event_count < 1:
        raise ValueError("event_count must be at least 1")

    scenario_names = ("standard", "express", "with_return")
    order_index = 0
    emitted = 0
    scenario_cycle = 0

    while emitted < event_count:
        scenario = scenario_names[scenario_cycle % len(scenario_names)]
        for action_cls in STORE_OCEL_SCENARIOS[scenario]:
            if emitted >= event_count:
                break
            yield StoreOcelTracePlanEntry(action_cls, order_index, scenario)
            emitted += 1
        order_index += 1
        scenario_cycle += 1


def build_store_ocel_machine(
    output_file: Path,
) -> tuple[ActionProductMachine, StoreOcelStoreResource]:
    """Return a machine with ``OcelPlugin`` and the store used as ``connections[ocel]``."""
    import_sample_registration_modules()
    store = StoreOcelStoreResource(output_file=output_file)
    machine = ActionProductMachine(
        graph_coordinator=build_registered_interchange_coordinator(),
        plugins=[OcelPlugin(store=store, short_names=True)],
    )
    return machine, store


def _params_for_order(entry: StoreOcelTracePlanEntry) -> StoreOcelTraceParams:
    order_index = entry.order_index
    order_id = f"ord-{order_index:04d}"
    suffix = f"{order_index:04d}"
    channel = "ecommerce" if order_index % 2 == 0 else "pos"
    return StoreOcelTraceParams(
        order_id=order_id,
        customer_id=f"cust-{suffix}",
        customer_name=f"Customer {suffix}",
        customer_email=f"customer{suffix}@store.example",
        amount=50.0 + float(order_index),
        storefront_channel=channel,
        line_id=f"line-{suffix}-a",
        product_id=f"prod-{suffix}",
        product_sku=f"SKU-{100 + order_index}",
        product_title=f"Product {suffix}",
        capture_id=f"pay-{suffix}",
        task_id=f"task-{suffix}",
        parcel_id=f"parcel-{suffix}",
        facility_id="wh-west-01" if order_index % 2 == 0 else "wh-east-02",
        return_id=f"ret-{suffix}",
        scenario=entry.scenario,
    )


async def run_store_ocel_trace_batch(
    machine: ActionProductMachine,
    store: StoreOcelStoreResource,
    *,
    trace_count: int,
    actions: Sequence[StoreOcelActionClass] | None = None,
    start_time: datetime | None = None,
    verbose: bool = False,
    output_file: Path | None = None,
) -> int:
    """Run ``trace_count`` storefront OCEL actions against one open store."""
    if trace_count < 1:
        raise ValueError("trace_count must be at least 1")

    if actions is None:
        plan = list(iter_store_ocel_trace_plan(trace_count))
    else:
        plan = [
            StoreOcelTracePlanEntry(
                actions[index % len(actions)],
                index // len(actions),
                "legacy",
            )
            for index in range(trace_count)
        ]

    if verbose:
        if output_file is not None:
            print(f"Output: {output_file}")
        print(
            f"Traces: {trace_count} "
            f"(scenarios: standard / express / with_return — payment, pick, parcel, return variants)\n"
        )

    await store.open()
    if verbose:
        print("Store opened.\n")

    base_time = start_time or datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)

    for index, entry in enumerate(plan):
        order_id = f"ord-{entry.order_index:04d}"
        customer_id = f"cust-{entry.order_index:04d}"
        trace_id = f"store-{entry.order_index:04d}-{entry.action_cls.__name__}"
        timestamp = base_time + timedelta(minutes=index)
        params = _params_for_order(entry)

        context = Context(
            request=RequestInfo(trace_id=trace_id, request_timestamp=timestamp),
        )
        result = cast(
            StoreOcelTraceResult,
            await machine.run(
                context,
                entry.action_cls(),
                params,
                connections={STORE_OCEL_CONNECTION_KEY: store},
            ),
        )
        if verbose:
            print(
                f"[{index + 1:>2}/{trace_count}] {entry.action_cls.__name__}"
                f"  scenario={entry.scenario}"
                f"  order={order_id}  customer={customer_id}"
                f"  trace={trace_id}  step={result.lifecycle_step}"
            )

    await store.close()
    if verbose:
        print("\nStore closed — JSON written.\n")
    return trace_count
