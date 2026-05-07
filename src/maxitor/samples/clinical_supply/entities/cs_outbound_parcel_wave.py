# src/maxitor/samples/clinical_supply/entities/cs_outbound_parcel_wave.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_care_site_unit import ClinicalCareSiteUnitEntity
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(description="Outbound dispatch header owned by ward / service desk", domain=ClinicalSupplyDomain)
class ClinicalOutboundParcelWaveEntity(BaseEntity):
    lifecycle: ClinicalSupplyLifecycle = Field(description="Outbound parcel lifecycle")
    id: str = Field(description="Parcel wave id")

    issuing_site: Annotated[
        AssociationOne[ClinicalCareSiteUnitEntity],
        NoInverse(),
    ] = Rel(description="Care unit authoring wave")  # type: ignore[assignment]


ClinicalOutboundParcelWaveEntity.model_rebuild()
