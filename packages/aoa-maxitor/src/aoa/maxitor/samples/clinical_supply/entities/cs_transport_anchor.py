# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_transport_anchor.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Cold-chain or courier modality row (transportation lookup analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalTransportAnchorEntity(BaseEntity):
    id: str = Field(description="Transport modality id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Transport catalog lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")


ClinicalTransportAnchorEntity.model_rebuild()
