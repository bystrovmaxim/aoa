# src/maxitor/samples/catalog/entities/catalog_bridge_shelf_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintEntity


@entity(description="Associative row sewing planogram island to bundle cardinality island", domain=CatalogDomain)
class CatalogShelfBundleLinkEntity(BaseEntity):
    id: str = Field(description="Assoc id")
    lifecycle: CatalogDenseLifecycle = Field(description="Link lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    shelf_hint: Annotated[
        AssociationOne[ShelfPlacementHintEntity],
        NoInverse(),
    ] = Rel(description="Planogram spine anchor")  # type: ignore[assignment]

    bundle_rule: Annotated[
        AssociationOne[BundleCardinalityRuleEntity],
        NoInverse(),
    ] = Rel(description="Bundle cardinality anchor")  # type: ignore[assignment]


CatalogShelfBundleLinkEntity.model_rebuild()
