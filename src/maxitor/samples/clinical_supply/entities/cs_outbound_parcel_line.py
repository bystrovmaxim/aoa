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
    lifecycle: ClinicalSupplyLifecycle = Field(description="Parcel line lifecycle")
    id: str = Field(description="Parcel line id")

    parcel_wave: Annotated[
        AssociationOne[ClinicalOutboundParcelWaveEntity],
        NoInverse(),
    ] = Rel(description="Parent parcel wave")  # type: ignore[assignment]

    consumable_row: Annotated[
        AssociationOne[ClinicalConsumableSkuEntity],
        NoInverse(),
    ] = Rel(description="Issued SKU")  # type: ignore[assignment]


ClinicalOutboundParcelLineEntity.model_rebuild()
