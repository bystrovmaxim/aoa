# src/maxitor/samples/catalog/entities/product_row.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_product_lifecycle import CatalogProductLifecycle


@entity(description="Sellable SKU in the sample catalog", domain=CatalogDomain)
class CatalogProductEntity(BaseEntity):
    id: str = Field(description="Product row id")
    lifecycle: CatalogProductLifecycle = Field(description="Catalog product lifecycle")
    sku: str = Field(description="Stock keeping unit")
    title: str = Field(description="Display title")
    list_price: float = Field(description="List price", ge=0)
