# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/catalog_merch_copy_variant.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.maxitor.samples.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintEntity


@entity(description="Merch copy chained from planogram hint spine", domain=CatalogDomain)
class MerchCopyVariantEntity(BaseEntity):
    id: str = Field(description="Variant id")
    lifecycle: CatalogDenseLifecycle = Field(description="Merch copy lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    shelf_hint: Annotated[
        AssociationOne[ShelfPlacementHintEntity],
        NoInverse(),
    ] = Rel(description="Owning shelf placement artefact")  # type: ignore[assignment]


MerchCopyVariantEntity.model_rebuild()
