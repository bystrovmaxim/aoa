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

    conversion_stub: Annotated[
        AssociationOne[ConversionAttributionStubEntity],
        NoInverse(),
    ] = Rel(description="Attribution conversion stub row")  # type: ignore[assignment]

    bundle_rule: Annotated[
        AssociationOne[BundleCardinalityRuleEntity],
        NoInverse(),
    ] = Rel(description="Cardinality island anchor")  # type: ignore[assignment]


AudienceSegmentGlueEntity.model_rebuild()
