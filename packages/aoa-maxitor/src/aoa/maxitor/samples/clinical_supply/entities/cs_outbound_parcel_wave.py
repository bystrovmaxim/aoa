# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_outbound_parcel_wave.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_care_site_unit import ClinicalCareSiteUnitEntity
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Outbound dispatch header owned by ward / service desk", domain=ClinicalSupplyDomain)
class ClinicalOutboundParcelWaveEntity(BaseEntity):
    id: str = Field(description="Parcel wave id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Outbound parcel lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    issuing_site: Annotated[
        AssociationOne[ClinicalCareSiteUnitEntity],
        NoInverse(),
    ] = Rel(description="Care unit authoring wave")  # type: ignore[assignment]


ClinicalOutboundParcelWaveEntity.model_rebuild()
