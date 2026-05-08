# src/maxitor/samples/store/actions/inventory_hold_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.store.domain import StoreDomain


@meta(description="Place inventory hold (store sample stub)", domain=StoreDomain)
@check_roles(NoneRole)
class InventoryHoldStubAction(BaseAction["InventoryHoldStubAction.Params", "InventoryHoldStubAction.Result"]):
    class Params(BaseParams):
        sku: str = Field(description="SKU")

    class Result(BaseResult):
        hold_id: str = Field(description="Stub reservation id")

    @summary_aspect("Hold")
    async def hold_summary(
        self,
        params: InventoryHoldStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> InventoryHoldStubAction.Result:
        return InventoryHoldStubAction.Result(hold_id=f"HOLD-{params.sku}")
