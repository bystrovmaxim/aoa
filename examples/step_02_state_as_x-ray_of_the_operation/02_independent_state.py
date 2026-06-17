"""
# 02_independent_state.py — each aspect creates an independent state snapshot

Every @regular_aspect receives a state snapshot and returns a new independent
snapshot for the next aspect. Fields continue only when explicitly forwarded.

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_int, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop order processing domain"


class ItemParams(BaseParams):
    raw_sku: str = Field(description="Raw SKU from client (may have extra spaces)")
    quantity: int = Field(description="Requested quantity")


class ItemResult(BaseResult):
    sku: str = Field(description="Normalised SKU")
    quantity: int = Field(description="Validated quantity")
    line_total: int = Field(description="Quantity * 100 (mock unit price)")


@meta(description="Process item through independent state snapshots", domain=ShopDomain)
@check_roles(NoneRole)
class ProcessItemAction(BaseAction[ItemParams, ItemResult]):

    @regular_aspect("Step 1: Normalise SKU")
    @result_string("sku", required=True, min_length=3)
    async def normalise_aspect(self, params, state, box, connections):
        return {"sku": params.raw_sku.strip().upper()}

    @regular_aspect("Step 2: Validate quantity and forward SKU")
    @result_string("sku", required=True)
    @result_int("quantity", required=True, min_value=1, max_value=100)
    async def validate_quantity_aspect(self, params, state, box, connections):
        return {
            "sku": state["sku"],
            "quantity": params.quantity,
        }

    @summary_aspect("Assemble line item")
    async def assemble_summary(self, params, state, box, connections):
        return ItemResult(
            sku=state["sku"],
            quantity=state["quantity"],
            line_total=state["quantity"] * 100,
        )


async def main() -> None:
    machine = ActionProductMachine()
    result = await machine.run(
        Context(),
        ProcessItemAction(),
        ItemParams(raw_sku="  abc-001  ", quantity=5),
    )
    print(f"sku={result.sku!r}, quantity={result.quantity}, line_total={result.line_total}")


asyncio.run(main())
