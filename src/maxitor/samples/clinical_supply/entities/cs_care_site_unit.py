# src/maxitor/samples/clinical_supply/entities/cs_care_site_unit.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle


@entity(
    description="Ward or service unit issuing outbound parcels (delivery department analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalCareSiteUnitEntity(BaseEntity):
    id: str = Field(description="Care unit id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Care unit lifecycle")


ClinicalCareSiteUnitEntity.model_rebuild()
