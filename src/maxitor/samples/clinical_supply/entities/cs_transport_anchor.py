# src/maxitor/samples/clinical_supply/entities/cs_transport_anchor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Cold-chain or courier modality row (transportation lookup analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalTransportAnchorEntity(BaseEntity):
    lifecycle: ClinicalSupplyLifecycle = Field(description="Transport catalog lifecycle")
    id: str = Field(description="Transport modality id")


ClinicalTransportAnchorEntity.model_rebuild()
