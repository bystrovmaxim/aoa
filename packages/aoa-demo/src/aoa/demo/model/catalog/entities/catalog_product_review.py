# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_product_review.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity
from aoa.demo.model.catalog.resources.catalog_object_store_storage import CatalogObjectStoreStorage


@entity(description="A customer's review of a product", resource=CatalogObjectStoreStorage)
class ProductReviewCoreEntity(BaseCoreEntity):
    id: str = Field(description="Review id")
    rating: int = Field(description="Stars the customer gave, from 1 to 5", ge=1, le=5)
    text: str = Field(description="What the customer wrote")
    product: Annotated[
        AssociationOne[CatalogProductCoreEntity],
        NoInverse(),
    ] = Field(description="Product the review is about")


ProductReviewCoreEntity.model_rebuild()
