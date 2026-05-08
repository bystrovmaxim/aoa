# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_partner_org_projection.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from aoa.maxitor.samples.clinical_supply.entities.cs_ownership_anchor import ClinicalOwnershipAnchorEntity
from aoa.maxitor.samples.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubEntity


@entity(
    description="Institutional subtype facts hanging off the partner hub (organization analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalPartnerOrgProjectionEntity(BaseEntity):
    id: str = Field(description="Org projection row id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Org subtype lifecycle")

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

    ownership_anchor: Annotated[
        AssociationOne[ClinicalOwnershipAnchorEntity],
        NoInverse(),
    ] = Rel(description="Corporate form catalog")  # type: ignore[assignment]


ClinicalPartnerOrgProjectionEntity.model_rebuild()
