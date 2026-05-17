# packages/aoa-examples/src/aoa/examples/model/catalog_custody/entities/regulated_stock_keeping_unit_row_entity.py
"""Regulated SKU anchor row for interchange / lifecycle demos."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain


@entity(description="Canonical regulated SKU custody row", domain=CatalogCustodyDomain)
class RegulatedStockKeepingUnitRowEntity(BaseEntity):
    sku_code: str = Field(description="Trade item identifier under custody regime")
    custody_tier: str = Field(description="Regulatory posture bucket (cold chain, pharma, DG, ... )")
    hazmat_class_stub: str = Field(description="Placeholder UN/GHS-derived hazard bucket")
    last_attested_revision: str = Field(description="Last lineage attest marker")
