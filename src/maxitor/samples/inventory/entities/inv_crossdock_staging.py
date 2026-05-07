# src/maxitor/samples/inventory/entities/inv_crossdock_staging.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_recall_signal import RecallSignalEntity


@entity(description="Cross-dock latch following recall signalling chain", domain=InventoryDomain)
class CrossDockStagingEntity(BaseEntity):
    id: str = Field(description="Staging id")
    lifecycle: InvDenseLifecycle = Field(description="Cross-dock staging lifecycle")

    recall_signal: Annotated[
        AssociationOne[RecallSignalEntity],
        NoInverse(),
    ] = Rel(description="Upstream recall signal")  # type: ignore[assignment]

    catalog_product_anchor: Annotated[
        AssociationOne["CatalogProductEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Catalog SKU keyed when diverting stock through cross-dock")  # type: ignore[assignment]


from maxitor.samples.catalog.entities.product_row import CatalogProductEntity  # noqa: E402

CrossDockStagingEntity.model_rebuild()
