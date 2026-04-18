# src/maxitor/samples/catalog/actions/price_snapshot.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.catalog.domain import CatalogDomain


class PriceSnapshotParams(BaseParams):
    sku: str = Field(description="SKU")


class PriceSnapshotResult(BaseResult):
    list_price: float = Field(description="Stub list price", ge=0)


@meta(description="Resolve list price snapshot (catalog sample stub)", domain=CatalogDomain)
@check_roles(NoneRole)
class PriceSnapshotAction(BaseAction[PriceSnapshotParams, PriceSnapshotResult]):
    @summary_aspect("Snapshot")
    async def snapshot_summary(
        self,
        params: PriceSnapshotParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> PriceSnapshotResult:
        return PriceSnapshotResult(list_price=float(len(params.sku)))
