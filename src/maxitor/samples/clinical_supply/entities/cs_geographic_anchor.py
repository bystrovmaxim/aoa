# src/maxitor/samples/clinical_supply/entities/cs_geographic_anchor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Geographic anchoring slice for supplier sites (catalog city analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalGeographicAnchorEntity(BaseEntity):
    lifecycle: ClinicalSupplyLifecycle = Field(description="Anchor lifecycle")
    id: str = Field(description="Geographic anchor id")


ClinicalGeographicAnchorEntity.model_rebuild()
