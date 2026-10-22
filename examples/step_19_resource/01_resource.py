"""The action decides; the resource stores.

Use an in-memory store so the only topic is the division between storage and the business decision.

Run: uv run python examples/step_19_resource/01_resource.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


class WarehouseDomain(BaseDomain):
    """Group the inventory example."""
    name = "warehouse"
    description = "Warehouse domain"


# ── Resource: transport only — read and write stock, no decisions ────────────
@meta(description="In-memory inventory store (transport only)", domain=WarehouseDomain)
class InventoryResource(BaseResource):

    """Read and update the supplied inventory."""
    def __init__(self, stock: dict[str, int] | None = None) -> None:
        """Initialize this example object."""
        self._stock: dict[str, int] = dict(stock or {})

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Choose the view supplied to child actions."""
        return None  # in-memory: direct pass-through; a SQL resource would return a wrapper

    async def get_stock(self, sku: str) -> int:
        """Read the available quantity."""
        return self._stock.get(sku, 0)

    async def take(self, sku: str, qty: int) -> None:
        """Subtract the supplied quantity."""
        self._stock[sku] = self._stock.get(sku, 0) - qty


class ReserveParams(BaseParams):
    """Describe the requested reservation."""
    sku: str = Field(description="Product code")
    qty: int = Field(gt=0, description="Quantity to reserve")


class ReserveResult(BaseResult):
    """Report the reservation decision."""
    reserved: bool = Field(description="Whether the reservation succeeded")
    remaining: int = Field(description="Stock left for this SKU")


@meta(description="Reserve stock for a SKU", domain=WarehouseDomain)
@check_roles(GuestRole)
@connection(InventoryResource, key="inventory")
class ReserveStockAction(BaseAction[ReserveParams, ReserveResult]):

    """Decide whether the requested stock is available."""

    @summary_aspect("Reserve if enough stock")
    async def reserve_summary(self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections) -> ReserveResult:
        """Reserve only when enough stock is available."""
        inventory = connections["inventory"]          # transport, supplied per request
        available = await inventory.get_stock(params.sku)
        # The DECISION lives here, in the Action — not in the Resource.
        if available < params.qty:
            return ReserveResult(reserved=False, remaining=available)
        await inventory.take(params.sku, params.qty)
        return ReserveResult(reserved=True, remaining=available - params.qty)


async def main():
    """Run this case and verify its observable result."""
    inventory = InventoryResource(stock={"sku-1": 10})
    result = await ActionProductMachine(loggers=[]).run(
        Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=3),
        connections={"inventory": inventory},
    )
    assert result.model_dump() == {'reserved': True, 'remaining': 7}
    print(result.model_dump())
    assert await inventory.get_stock("sku-1") == 7


if __name__ == "__main__":
    asyncio.run(main())
