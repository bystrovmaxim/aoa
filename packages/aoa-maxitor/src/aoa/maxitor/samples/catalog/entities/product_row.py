# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/product_row.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.entities.catalog_product_lifecycle import CatalogProductLifecycle


@entity(description="Sellable SKU in the sample catalog", domain=CatalogDomain)
class CatalogProductEntity(BaseEntity):
    id: str = Field(description="Product row id")
    lifecycle: CatalogProductLifecycle = Field(description="Catalog product lifecycle")
    sku: str = Field(description="Stock keeping unit")
    title: str = Field(description="Display title")
    list_price: float = Field(description="List price", ge=0)
    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
