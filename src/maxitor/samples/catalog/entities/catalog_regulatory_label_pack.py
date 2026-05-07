# src/maxitor/samples/catalog/entities/catalog_regulatory_label_pack.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_merch_copy_variant import MerchCopyVariantEntity


@entity(description="Regulatory label continuation of planogram / copy spine", domain=CatalogDomain)
class RegulatoryLabelPackEntity(BaseEntity):
    lifecycle: CatalogDenseLifecycle = Field(description="Regulatory pack lifecycle")
    id: str = Field(description="Pack id")

    merch_copy: Annotated[
        AssociationOne[MerchCopyVariantEntity],
        NoInverse(),
    ] = Rel(description="Parent merch variant row")  # type: ignore[assignment]


RegulatoryLabelPackEntity.model_rebuild()
