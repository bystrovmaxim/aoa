"""Record only the fact of a connection.

This record says that one product belongs to one category. Its identifier and creation timestamp are service data. There is no price, quantity, or agreement to describe.

Run: uv run python examples/step_22_entity/04_association.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseAssocEntity, BaseCoreEntity, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where ShopStorage keeps its rows")
class ShopDataSource(InMemoryDataSource):
    """The store ShopStorage works with."""


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage[ShopDataSource]):
    """Hold the shop entities."""


@entity(description="Product", resource=ShopStorage)
class ProductCoreEntity(BaseCoreEntity):
    """Identify a product in the catalogue."""

    id: str = Field(description="Product identifier")


@entity(description="Catalogue category", resource=ShopStorage)
class CategoryCoreEntity(BaseCoreEntity):
    """Identify a category used to organise products."""

    id: str = Field(description="Category identifier")


@entity(description="Product membership in a category", resource=ShopStorage)
class ProductCategoryAssocEntity(BaseAssocEntity):
    """Record a technical connection between product and category."""

    id: str = Field(description="Storage identifier of the link")
    created_at: str = Field(description="Storage insertion timestamp")
    product: Annotated[AssociationOne[ProductCoreEntity], NoInverse()] = Field(description="Linked product")
    category: Annotated[AssociationOne[CategoryCoreEntity], NoInverse()] = Field(description="Linked category")

link = ProductCategoryAssocEntity(
    id="link-1", created_at="2026-10-22T09:00:00Z",
    product=AssociationOne[ProductCoreEntity](id="product-1"),
    category=AssociationOne[CategoryCoreEntity](id="category-1"),
)
assert link.product.id == "product-1" and link.category.id == "category-1"
print(link.product.id, "belongs to", link.category.id)
