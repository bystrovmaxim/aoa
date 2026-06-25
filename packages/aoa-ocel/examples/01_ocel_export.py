"""
01_ocel_export.py — export one AOA action run as an OCEL 2.0 log.

A minimal "order created" action returns an ``OcelFrame`` for the order with its
``customer`` relation loaded. ``OcelPlugin`` turns the trace into one OCEL event
(root E2O + one-hop peer E2O), ``InMemoryOcelStoreResource`` writes OCEL 2.0 JSON,
and this script prints a readable summary plus the pretty log.

Run from repository root:
    uv run --extra dev python packages/aoa-ocel/examples/01_ocel_export.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.domain import (
    AssociationOne,
    BaseEntity,
    NoInverse,
    Rel,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.ocel import OCEL_FRAMES_KEY, InMemoryOcelStoreResource, OcelFrame, OcelPlugin
from aoa.ocel.dto import OcelAttribute


# ── Minimal inline domain ────────────────────────────────────────────────────
class ShopDomain(BaseDomain):
    name = "shop"
    description = "Tiny order-and-customer shop domain"


@meta(description="Customer placing orders", domain=ShopDomain)
@entity(description="Customer placing orders", domain=ShopDomain)
class CustomerEntity(BaseEntity):
    id: str = Field(description="Customer identifier")
    name: str = Field(description="Customer name")


@meta(description="Order created in the shop", domain=ShopDomain)
@entity(description="Order created in the shop", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order identifier")
    sku: str = Field(description="Ordered SKU")
    customer: Annotated[
        AssociationOne[CustomerEntity] | None,
        NoInverse(),
    ] = Rel(description="Customer who placed the order")  # type: ignore[assignment]


# ── Action that emits an OcelFrame ───────────────────────────────────────────
class CreateOrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")
    sku: str = Field(description="Ordered SKU")
    customer_id: str = Field(description="Customer identifier")
    customer_name: str = Field(description="Customer name")


class CreateOrderResult(BaseResult):
    message: str = Field(description="Human-readable summary")


@meta(description="Create order and emit OCEL frame", domain=ShopDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):
    @regular_aspect("Export OCEL frame")
    @result_instance(OCEL_FRAMES_KEY, (OcelFrame, list), required=True)
    async def export_aspect(
        self,
        params: CreateOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        # Partial load: the customer relation IS loaded, so it participates in E2O.
        customer = CustomerEntity(id=params.customer_id, name=params.customer_name)
        order = OrderEntity(
            id=params.order_id,
            sku=params.sku,
            customer=AssociationOne(id=customer.id, entity=customer),
        )
        return {
            OCEL_FRAMES_KEY: [
                OcelFrame(
                    object=order,
                    qualifier="Created order with identifier",
                    attributes=[OcelAttribute(name="domain", value="shop")],
                ),
            ]
        }

    @summary_aspect("Build result")
    @result_string("message", required=True, min_length=1)
    async def build_summary(
        self,
        params: CreateOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> CreateOrderResult:
        return CreateOrderResult(
            message=f"Order {params.order_id} created for {params.customer_name}",
        )


def _summarize(doc: dict[str, Any]) -> str:
    events = doc["events"]
    objects = doc["objects"]
    qualifiers = sorted({rel["qualifier"] for ev in events for rel in ev["relationships"]})
    lines = [
        f"events ............. {len(events)}",
        f"objects ............ {len(objects)}",
        f"event types ........ {', '.join(t['name'] for t in doc['eventTypes'])}",
        f"object types ....... {', '.join(t['name'] for t in doc['objectTypes'])}",
        f"E2O qualifiers ..... {', '.join(qualifiers)}",
    ]
    return "\n".join(lines)


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "shop.ocel.json"

        # The owning connection opens/closes the store; the plugin only adds events.
        store = InMemoryOcelStoreResource(output_file=output)
        await store.open()

        machine = ActionProductMachine(plugins=[OcelPlugin(store=store)])
        context = Context(
            request=RequestInfo(
                trace_id="trace-order-001",
                request_timestamp=datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC),
            ),
        )
        result = await machine.run(
            context,
            CreateOrderAction(),
            CreateOrderParams(
                order_id="order_1",
                sku="SKU-42",
                customer_id="cust_7",
                customer_name="Ada Lovelace",
            ),
        )

        await store.close()  # writes OCEL 2.0 JSON
        doc = json.loads(output.read_text(encoding="utf-8"))

    print(result.message)
    print()
    print("OCEL 2.0 summary")
    print("================")
    print(_summarize(doc))
    print()
    print("OCEL 2.0 log")
    print("============")
    print(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
