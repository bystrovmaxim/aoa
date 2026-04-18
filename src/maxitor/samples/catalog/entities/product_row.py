# src/maxitor/samples/catalog/entities/product_row.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity, entity
from maxitor.samples.catalog.domain import CatalogDomain


@entity(description="Sellable SKU in the sample catalog", domain=CatalogDomain)
class CatalogProductEntity(BaseEntity):
    sku: str = Field(description="Stock keeping unit")
    title: str = Field(description="Display title")
    list_price: float = Field(description="List price", ge=0)
