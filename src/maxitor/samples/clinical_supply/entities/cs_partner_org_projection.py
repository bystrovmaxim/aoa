# src/maxitor/samples/clinical_supply/entities/cs_partner_org_projection.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_ownership_anchor import ClinicalOwnershipAnchorEntity
from maxitor.samples.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubEntity


@entity(
    description="Institutional subtype facts hanging off the partner hub (organization analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalPartnerOrgProjectionEntity(BaseEntity):
    id: str = Field(description="Org projection row id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Org subtype lifecycle")

    partner_hub: Annotated[
        AssociationOne[ClinicalPartnerHubEntity],
        NoInverse(),
    ] = Rel(description="Parent partner aggregate")  # type: ignore[assignment]

    ownership_anchor: Annotated[
        AssociationOne[ClinicalOwnershipAnchorEntity],
        NoInverse(),
    ] = Rel(description="Corporate form catalog")  # type: ignore[assignment]


ClinicalPartnerOrgProjectionEntity.model_rebuild()
