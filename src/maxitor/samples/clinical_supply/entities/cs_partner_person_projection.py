# src/maxitor/samples/clinical_supply/entities/cs_partner_person_projection.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubEntity


@entity(
    description="Individual subtype facts hanging off the partner hub (person analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalPartnerPersonProjectionEntity(BaseEntity):
    id: str = Field(description="Person projection row id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Person subtype lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    partner_hub: Annotated[
        AssociationOne[ClinicalPartnerHubEntity],
        NoInverse(),
    ] = Rel(description="Parent partner aggregate")  # type: ignore[assignment]


ClinicalPartnerPersonProjectionEntity.model_rebuild()
