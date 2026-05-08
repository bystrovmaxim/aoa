# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_ownership_anchor.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Legal ownership pattern catalog for institutional partners",
    domain=ClinicalSupplyDomain,
)
class ClinicalOwnershipAnchorEntity(BaseEntity):
    id: str = Field(description="Ownership pattern id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Ownership catalog lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")


ClinicalOwnershipAnchorEntity.model_rebuild()
