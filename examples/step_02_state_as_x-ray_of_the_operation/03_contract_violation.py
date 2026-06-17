"""
# 03_contract_violation.py — checker failure stops the pipeline immediately

When an aspect returns a dict that violates a @result_* checker, the machine
raises ValidationFieldError before the next step starts.

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
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
    raw_sku: str = Field(description="Raw SKU from client")
    quantity: int = Field(description="Requested quantity")


class ItemResult(BaseResult):
    sku: str = Field(description="Normalised SKU")
    quantity: int = Field(description="Validated quantity")
    line_total: int = Field(description="Quantity * 100 (mock unit price)")


@meta(description="Aspect that returns an incomplete state dict", domain=ShopDomain)
@check_roles(NoneRole)
class BrokenItemAction(BaseAction[ItemParams, ItemResult]):

    @regular_aspect("Intentionally broken step")
    @result_string("sku", required=True)
    @result_int("quantity", required=True, min_value=1)
    async def broken_aspect(self, params, state, box, connections):
        return {"quantity": params.quantity}

    @summary_aspect("Never reached")
    async def never_summary(self, params, state, box, connections):
        return ItemResult(sku="?", quantity=0, line_total=0)


async def main() -> None:
    machine = ActionProductMachine()
    params = ItemParams(raw_sku="abc", quantity=3)
    try:
        await machine.run(Context(), BrokenItemAction(), params)
    except ValidationFieldError as exc:
        print(f"ValidationFieldError: {exc}")
        print("(Next step never ran — error is immediate)")


asyncio.run(main())
