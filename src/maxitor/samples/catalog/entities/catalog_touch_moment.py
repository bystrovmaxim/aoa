# src/maxitor/samples/catalog/entities/catalog_touch_moment.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Attributed touch moment", domain=CatalogDomain)
class TouchMomentEntity(BaseEntity):
    id: str = Field(description="Touch id")
    lifecycle: CatalogDenseLifecycle = Field(description="Touch lifecycle")

    channel_ledger: Annotated[
        AssociationOne[AcquisitionChannelLedgerEntity],
        NoInverse(),
    ] = Rel(description="Acquisition ledger segment")  # type: ignore[assignment]


TouchMomentEntity.model_rebuild()
