# src/maxitor/samples/catalog/entities/catalog_audience_segment_glue.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleEntity
from maxitor.samples.catalog.entities.catalog_conversion_attribution_stub import ConversionAttributionStubEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Diamond bridge: merges acquisition funnel with assortment island (still no SKU star)", domain=CatalogDomain)
class AudienceSegmentGlueEntity(BaseEntity):
    id: str = Field(description="Glue id")
    lifecycle: CatalogDenseLifecycle = Field(description="Glue lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    conversion_stub: Annotated[
        AssociationOne[ConversionAttributionStubEntity],
        NoInverse(),
    ] = Rel(description="Attribution conversion stub row")  # type: ignore[assignment]

    bundle_rule: Annotated[
        AssociationOne[BundleCardinalityRuleEntity],
        NoInverse(),
    ] = Rel(description="Cardinality island anchor")  # type: ignore[assignment]


AudienceSegmentGlueEntity.model_rebuild()
