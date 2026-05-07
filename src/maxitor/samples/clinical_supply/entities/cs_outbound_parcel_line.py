# src/maxitor/samples/clinical_supply/entities/cs_outbound_parcel_line.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_consumable_sku_row import ClinicalConsumableSkuEntity
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_outbound_parcel_wave import ClinicalOutboundParcelWaveEntity


@entity(
    description="Line grain tying parcel wave with SKU issuance quantity (delivery string analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalOutboundParcelLineEntity(BaseEntity):
    id: str = Field(description="Parcel line id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Parcel line lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    parcel_wave: Annotated[
        AssociationOne[ClinicalOutboundParcelWaveEntity],
        NoInverse(),
    ] = Rel(description="Parent parcel wave")  # type: ignore[assignment]

    consumable_row: Annotated[
        AssociationOne[ClinicalConsumableSkuEntity],
        NoInverse(),
    ] = Rel(description="Issued SKU")  # type: ignore[assignment]


ClinicalOutboundParcelLineEntity.model_rebuild()
