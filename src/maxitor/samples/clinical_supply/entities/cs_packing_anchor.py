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

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")


ClinicalPackingAnchorEntity.model_rebuild()
