# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_search_boost_weight.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.entities.catalog_search_lifecycle import CatalogSearchLifecycle
from aoa.demo.model.catalog.resources.catalog_search_sidecar_storage import CatalogSearchSidecarStorage


@entity(description="Search boost chaining off availability subtree", resource=CatalogSearchSidecarStorage)
class SearchBoostWeightCoreEntity(BaseCoreEntity):
    id: str = Field(description="Boost id")
    lifecycle: CatalogSearchLifecycle = Field(description="Search boost lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)


SearchBoostWeightCoreEntity.model_rebuild()
