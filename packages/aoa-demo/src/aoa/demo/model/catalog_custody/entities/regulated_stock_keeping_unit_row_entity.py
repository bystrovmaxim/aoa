# packages/aoa-demo/src/aoa/demo/model/catalog_custody/entities/regulated_stock_keeping_unit_row_entity.py
"""Regulated SKU anchor row for interchange / lifecycle demos."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseDetailEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity
from aoa.demo.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain


@entity(description="Canonical regulated SKU custody row", domain=CatalogCustodyDomain)
class RegulatedStockKeepingUnitRowDetailEntity(BaseDetailEntity):
    sku_code: str = Field(description="Trade item identifier under custody regime")
    custody_tier: str = Field(description="Regulatory posture bucket (cold chain, pharma, DG, ... )")
    hazmat_class_stub: str = Field(description="Placeholder UN/GHS-derived hazard bucket")
    last_attested_revision: str = Field(description="Last lineage attest marker")
    product: Annotated[
        AssociationOne[CatalogProductCoreEntity],
        NoInverse(),
    ] = Field(description="The catalog product the custody rules apply to")
