# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/catalog_availability_projection.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Availability projection subgraph root independent of SKU FK", domain=CatalogDomain)
class AvailabilityProjectionEntity(BaseEntity):
    id: str = Field(description="Projection id")
    lifecycle: CatalogDenseLifecycle = Field(description="Availability projection lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)


AvailabilityProjectionEntity.model_rebuild()
