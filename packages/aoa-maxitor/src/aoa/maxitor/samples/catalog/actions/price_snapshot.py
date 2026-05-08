# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/actions/price_snapshot.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.catalog.domain import CatalogDomain


@meta(description="Resolve list price snapshot (catalog sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class PriceSnapshotAction(BaseAction["PriceSnapshotAction.Params", "PriceSnapshotAction.Result"]):
    class Params(BaseParams):
        sku: str = Field(description="SKU")

    class Result(BaseResult):
        list_price: float = Field(description="Stub list price", ge=0)

    @summary_aspect("Snapshot")
    async def snapshot_summary(
        self,
        params: PriceSnapshotAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> PriceSnapshotAction.Result:
        return PriceSnapshotAction.Result(list_price=float(len(params.sku)))
