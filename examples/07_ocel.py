"""
Scenario: OCEL 2.0 event log.

OcelPlugin records each Action run in OCEL 2.0 format when aspects return
``OcelFrame`` rows (see ``OCEL_FRAMES_KEY``). InMemoryOcelStoreResource keeps
events in memory and writes them to a file on ``close()``.

Install:
    pip install "aoa-action-machine[ocel]"

Run:
    uv run python examples/07_ocel.py
"""
import asyncio
import json
from pathlib import Path

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.ocel import InMemoryOcelStoreResource, OCEL_FRAMES_KEY, OcelFrame, OcelPlugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


@entity(description="Order", domain=RootDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order ID")


class OrderParams(BaseParams):
    order_id: str = Field(description="Order ID")


class OrderResult(BaseResult):
    order_id: str = Field(description="Created order ID")


@meta(description="Create order", domain=RootDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

    @regular_aspect("Validation")
    @result_string("validated_id", required=True)
    @result_instance(OCEL_FRAMES_KEY, list, required=False)
    async def validate_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "Validate order: id={%var.order_id}",
            order_id=params.order_id,
        )
        order = OrderEntity(id=params.order_id)
        return {
            "validated_id": params.order_id,
            OCEL_FRAMES_KEY: [
                OcelFrame(object=order, qualifier="Create order"),
            ],
        }

    @summary_aspect("Create")
    async def create_summary(self, params, state, box, connections):
        return OrderResult(order_id=str(state["validated_id"]))


async def main() -> None:
    output = Path("ocel_log.json")
    store = InMemoryOcelStoreResource(output_file=output)

    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
        plugins=[OcelPlugin(store=store, short_names=True)],
    )

    print("Sample 07 ocel\n")
    await store.open()
    for order_id in ["ord-001", "ord-002", "ord-003"]:
        await machine.run(
            Context(),
            CreateOrderAction(),
            params=OrderParams(order_id=order_id),
        )

    await store.close()
    data = json.loads(output.read_text())
    print("\n" + f"written: {output}")
    print(f"events: {len(data.get('events', []))}")


asyncio.run(main())
