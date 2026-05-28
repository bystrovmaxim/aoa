"""
Minimal working example: CreateOrder with summary aspect only.

Run:
    uv run python examples/01_hello_world.py
"""
import asyncio
import uuid

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")


@meta(description="Create order", domain=StoreDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction[ParamsStub, CreateOrderResult]):

    @summary_aspect("Build action result")
    async def create_summary(self, params, state, box, connections):
        return CreateOrderResult(order_id=f"ord-{uuid.uuid4().hex[:8]}")


async def main() -> None:
    machine = ActionProductMachine()
    order_result = await machine.run(Context(), CreateOrderAction(), ParamsStub())
    print(order_result.order_id)


asyncio.run(main())
