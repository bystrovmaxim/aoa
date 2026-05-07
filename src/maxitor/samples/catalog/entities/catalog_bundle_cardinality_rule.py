# src/maxitor/samples/catalog/entities/catalog_bundle_cardinality_rule.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Bundle cardinality island root for cross-subgraph bridging only", domain=CatalogDomain)
class BundleCardinalityRuleEntity(BaseEntity):
    id: str = Field(description="Rule id")
    lifecycle: CatalogDenseLifecycle = Field(description="Bundle cardinality lifecycle")


BundleCardinalityRuleEntity.model_rebuild()
