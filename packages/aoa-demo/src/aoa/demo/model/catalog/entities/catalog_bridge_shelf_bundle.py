# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_bridge_shelf_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleCoreEntity
from aoa.demo.model.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.demo.model.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintCoreEntity


@entity(description="Associative row sewing planogram island to bundle cardinality island", domain=CatalogDomain)
class CatalogShelfBundleLinkCoreEntity(BaseCoreEntity):
    id: str = Field(description="Assoc id")
    lifecycle: CatalogDenseLifecycle = Field(description="Link lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    shelf_hint: Annotated[
        AssociationOne[ShelfPlacementHintCoreEntity],
        NoInverse(),
    ] = Field(
        description="Planogram spine anchor"
    )

    bundle_rule: Annotated[
        AssociationOne[BundleCardinalityRuleCoreEntity],
        NoInverse(),
    ] = Field(
        description="Bundle cardinality anchor"
    )


CatalogShelfBundleLinkCoreEntity.model_rebuild()
