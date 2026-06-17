"""
# 04_contract_preserving_step.py — inserting a step without breaking downstream state

A new aspect inserted in the middle of a pipeline must explicitly preserve the
state contract expected by downstream aspects.

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.py
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


@meta(description="Baseline flow: normalise item and assemble result", domain=ShopDomain)
@check_roles(NoneRole)
class BaselineItemAction(BaseAction[ItemParams, ItemResult]):

    @regular_aspect("Normalise item")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1)
    async def normalise_aspect(self, params, state, box, connections):
        return {
            "sku": params.raw_sku.strip().upper(),
            "quantity": params.quantity,
        }

    @summary_aspect("Assemble result")
    async def assemble_summary(self, params, state, box, connections):
        return ItemResult(
            sku=state["sku"],
            quantity=state["quantity"],
            line_total=state["quantity"] * 100,
        )


@meta(description="Flow with an inserted informational step", domain=ShopDomain)
@check_roles(NoneRole)
class WithInformingStepAction(BaseAction[ItemParams, ItemResult]):

    @regular_aspect("Normalise item")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1)
    async def normalise_aspect(self, params, state, box, connections):
        return {
            "sku": params.raw_sku.strip().upper(),
            "quantity": params.quantity,
        }

    @regular_aspect("Inform operator without changing business state")
    @result_string("sku", required=True, min_length=3)
    @result_int("quantity", required=True, min_value=1)
    async def inform_aspect(self, params, state, box, connections):
        return {
            "sku": state["sku"],
            "quantity": state["quantity"],
        }

    @summary_aspect("Assemble result")
    async def assemble_summary(self, params, state, box, connections):
        return ItemResult(
            sku=state["sku"],
            quantity=state["quantity"],
            line_total=state["quantity"] * 100,
        )


async def main() -> None:
    params = ItemParams(raw_sku="  abc-001  ", quantity=5)
    machine = ActionProductMachine()
    baseline = await machine.run(Context(), BaselineItemAction(), params)
    with_informing = await machine.run(Context(), WithInformingStepAction(), params)
    print(f"baseline result       = sku={baseline.sku!r}, quantity={baseline.quantity}, line_total={baseline.line_total}")
    print(
        f"with informing step   = sku={with_informing.sku!r}, "
        f"quantity={with_informing.quantity}, line_total={with_informing.line_total}"
    )
    print("inform_aspect is allowed only because it preserves the downstream state contract")


asyncio.run(main())
