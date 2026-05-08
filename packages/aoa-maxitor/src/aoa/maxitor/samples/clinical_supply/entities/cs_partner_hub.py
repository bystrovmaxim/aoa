# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_partner_hub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_geographic_anchor import ClinicalGeographicAnchorEntity
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Neutral partner root keyed for subtype projections", domain=ClinicalSupplyDomain)
class ClinicalPartnerHubEntity(BaseEntity):
    id: str = Field(description="Partner id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Partner lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    site_anchor: Annotated[
        AssociationOne[ClinicalGeographicAnchorEntity],
        NoInverse(),
    ] = Rel(description="Registered geography")  # type: ignore[assignment]


ClinicalPartnerHubEntity.model_rebuild()
