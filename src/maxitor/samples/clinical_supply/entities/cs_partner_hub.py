# src/maxitor/samples/clinical_supply/entities/cs_partner_hub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_geographic_anchor import ClinicalGeographicAnchorEntity
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Neutral partner root keyed for subtype projections", domain=ClinicalSupplyDomain)
class ClinicalPartnerHubEntity(BaseEntity):
    lifecycle: ClinicalSupplyLifecycle = Field(description="Partner lifecycle")
    id: str = Field(description="Partner id")

    site_anchor: Annotated[
        AssociationOne[ClinicalGeographicAnchorEntity],
        NoInverse(),
    ] = Rel(description="Registered geography")  # type: ignore[assignment]


ClinicalPartnerHubEntity.model_rebuild()
