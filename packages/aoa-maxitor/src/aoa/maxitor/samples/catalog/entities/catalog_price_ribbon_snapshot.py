# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/catalog_price_ribbon_snapshot.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.maxitor.samples.catalog.entities.catalog_search_boost_weight import SearchBoostWeightEntity


@entity(description="Price ribbon chained from search/boost spine (still no SKU hop)", domain=CatalogDomain)
class PriceRibbonSnapshotEntity(BaseEntity):
    id: str = Field(description="Ribbon id")
    lifecycle: CatalogDenseLifecycle = Field(description="Price ribbon lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    search_boost: Annotated[
        AssociationOne[SearchBoostWeightEntity],
        NoInverse(),
    ] = Rel(description="Upstream search/boost facet")  # type: ignore[assignment]


PriceRibbonSnapshotEntity.model_rebuild()
