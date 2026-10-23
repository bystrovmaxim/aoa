# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_bridge_price_acquisition.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerCoreEntity
from aoa.demo.model.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.demo.model.catalog.entities.catalog_price_ribbon_snapshot import PriceRibbonSnapshotCoreEntity


@entity(
    description="Associative stitching between attribution ledger and elasticity ribbon subgraph", domain=CatalogDomain
)
class CatalogPriceAcquisitionLinkCoreEntity(BaseCoreEntity):
    id: str = Field(description="Link id")
    lifecycle: CatalogDenseLifecycle = Field(description="Stitch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    price_ribbon: Annotated[
        AssociationOne[PriceRibbonSnapshotCoreEntity],
        NoInverse(),
    ] = Field(
        description="Ribbon spine anchor"
    )

    acquisition_ledger: Annotated[
        AssociationOne[AcquisitionChannelLedgerCoreEntity],
        NoInverse(),
    ] = Field(
        description="Acquisition ledger anchor"
    )


CatalogPriceAcquisitionLinkCoreEntity.model_rebuild()
