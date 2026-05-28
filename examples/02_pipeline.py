"""
CreateOrder pipeline: regular → summary, checkers, state.

Run:
    uv run python examples/02_pipeline.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class CreateOrderParams(BaseParams):
    order_id: str = Field(description="Order ID")


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Created order ID")
    reservation_id: str = Field(description="Reservation ID")


@meta(description="Create order", domain=StoreDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    @regular_aspect("Validation")
    @result_string("validated_id", required=True, min_length=1)
    async def validate_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[1] regular: validate order={%var.order_id}",
            order_id=params.order_id,
        )
        return {"validated_id": params.order_id}

    @regular_aspect("Reserve")
    @result_string("validated_id", required=True, min_length=1)
    @result_string("reservation_id", required=True, min_length=1)
    async def reserve_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[2] regular: reserve validated_id={%var.validated_id}",
            validated_id=state["validated_id"],
        )
        return {
            "validated_id": state["validated_id"],
            "reservation_id": f"res-{state['validated_id']}",
        }

    @summary_aspect("Create")
    async def create_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[3] summary: order={%var.order_id}, reservation={%var.reservation_id}",
            order_id=state["validated_id"],
            reservation_id=state["reservation_id"],
        )
        return CreateOrderResult(
            order_id=state["validated_id"],
            reservation_id=state["reservation_id"],
        )


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    print("Sample 02 pipeline\n")
    result = await machine.run(
        Context(),
        CreateOrderAction(),
        params=CreateOrderParams(order_id="ord-001"),
    )
    print(
        f"\nResult: order_id={result.order_id}, "
        f"reservation_id={result.reservation_id}"
    )


asyncio.run(main())
