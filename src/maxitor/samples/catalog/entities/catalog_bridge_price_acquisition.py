# src/maxitor/samples/catalog/entities/catalog_bridge_price_acquisition.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_price_ribbon_snapshot import PriceRibbonSnapshotEntity


@entity(description="Associative stitching between attribution ledger and elasticity ribbon subgraph", domain=CatalogDomain)
class CatalogPriceAcquisitionLinkEntity(BaseEntity):
    id: str = Field(description="Link id")
    lifecycle: CatalogDenseLifecycle = Field(description="Stitch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    price_ribbon: Annotated[
        AssociationOne[PriceRibbonSnapshotEntity],
        NoInverse(),
    ] = Rel(description="Ribbon spine anchor")  # type: ignore[assignment]

    acquisition_ledger: Annotated[
        AssociationOne[AcquisitionChannelLedgerEntity],
        NoInverse(),
    ] = Rel(description="Acquisition ledger anchor")  # type: ignore[assignment]


CatalogPriceAcquisitionLinkEntity.model_rebuild()
