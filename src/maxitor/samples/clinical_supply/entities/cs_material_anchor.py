# src/maxitor/samples/clinical_supply/entities/cs_material_anchor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Sterility / compound family catalog for SKU rows", domain=ClinicalSupplyDomain)
class ClinicalMaterialAnchorEntity(BaseEntity):
    id: str = Field(description="Material family id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Material catalog lifecycle")


ClinicalMaterialAnchorEntity.model_rebuild()
