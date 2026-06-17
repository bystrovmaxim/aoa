"""
01_resource.py — Resource as pure transport, separate from the Action

AOA splits two beings that ordinary services blur together:

  - Action   — no memory: each call starts clean, everything arrives via Params,
               state, dependencies. It holds the *decisions*.
  - Resource — long-lived state: a connection, a pool, a client, a store that
               must live across calls. It holds the *transport* only — open,
               execute, return. No business rules.

Golden rule: state outlives one call -> Resource; state lives only inside the
call -> Action. A Resource subclasses BaseResource, declares @meta, and
implements get_wrapper_class() (None = direct pass-through; a transactional
resource returns a wrapper that blocks commit/rollback in nested actions).

Because the decision lives in the Action and the transport in the Resource, the
Action is tested by swapping the Resource — same operation, different store.

Tutorial: ../../docs/tutorials/step-19-resource_draft.md  ·  topic: Resource

Run:
    uv run python examples/step_19_resource/01_resource.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class WarehouseDomain(BaseDomain):
    name = "warehouse"
    description = "Warehouse domain"


# ── Resource: transport only — read and write stock, no decisions ────────────
@meta(description="In-memory inventory store (transport only)", domain=WarehouseDomain)
class InventoryResource(BaseResource):

    def __init__(self, stock: dict[str, int] | None = None) -> None:
        self._stock: dict[str, int] = dict(stock or {})

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None  # in-memory: direct pass-through; a SQL resource would return a wrapper

    async def get_stock(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    async def take(self, sku: str, qty: int) -> None:
        self._stock[sku] = self._stock.get(sku, 0) - qty


class ReserveParams(BaseParams):
    sku: str = Field(description="Product code")
    qty: int = Field(gt=0, description="Quantity to reserve")


class ReserveResult(BaseResult):
    reserved: bool = Field(description="Whether the reservation succeeded")
    remaining: int = Field(description="Stock left for this SKU")


@meta(description="Reserve stock for a SKU", domain=WarehouseDomain)
@check_roles(NoneRole)
@connection(InventoryResource, key="inventory")
class ReserveStockAction(BaseAction[ReserveParams, ReserveResult]):

    @summary_aspect("Reserve if enough stock")
    async def reserve_summary(self, params, state, box, connections):
        inventory = connections["inventory"]          # transport, supplied per request
        available = await inventory.get_stock(params.sku)
        # The DECISION lives here, in the Action — not in the Resource.
        if available < params.qty:
            return ReserveResult(reserved=False, remaining=available)
        await inventory.take(params.sku, params.qty)
        return ReserveResult(reserved=True, remaining=available - params.qty)


async def main() -> None:
    machine = ActionProductMachine()

    print("Real inventory (sku-1: 10 in stock):")
    real = InventoryResource(stock={"sku-1": 10})
    for qty in (3, 99):
        r = await machine.run(Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=qty),
                              connections={"inventory": real})
        print(f"  reserve {qty:<3} -> reserved={r.reserved}, remaining={r.remaining}")

    print("\nSwapped resource (empty store, same Action):")
    empty = InventoryResource(stock={})
    r = await machine.run(Context(), ReserveStockAction(), ReserveParams(sku="sku-1", qty=1),
                          connections={"inventory": empty})
    print(f"  reserve 1   -> reserved={r.reserved}, remaining={r.remaining}")


asyncio.run(main())
