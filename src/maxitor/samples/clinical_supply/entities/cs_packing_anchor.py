# src/maxitor/samples/clinical_supply/entities/cs_packing_anchor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Sterile tray / carton profile for inbound lots", domain=ClinicalSupplyDomain)
class ClinicalPackingAnchorEntity(BaseEntity):
    id: str = Field(description="Packing profile id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Packing catalog lifecycle")


ClinicalPackingAnchorEntity.model_rebuild()
