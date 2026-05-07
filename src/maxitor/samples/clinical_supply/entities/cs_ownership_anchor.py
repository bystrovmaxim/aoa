# src/maxitor/samples/clinical_supply/entities/cs_ownership_anchor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Legal ownership pattern catalog for institutional partners",
    domain=ClinicalSupplyDomain,
)
class ClinicalOwnershipAnchorEntity(BaseEntity):
    id: str = Field(description="Ownership pattern id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Ownership catalog lifecycle")


ClinicalOwnershipAnchorEntity.model_rebuild()
