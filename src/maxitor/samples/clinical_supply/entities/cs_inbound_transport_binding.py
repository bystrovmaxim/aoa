# src/maxitor/samples/clinical_supply/entities/cs_inbound_transport_binding.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_inbound_shipment_ticket import (
    ClinicalInboundShipmentTicketEntity,
)
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_transport_anchor import ClinicalTransportAnchorEntity


@entity(
    description="Associative modality bind between inbound ticket and courier channel (M:N bridge)",
    domain=ClinicalSupplyDomain,
)
class ClinicalInboundTransportBindingEntity(BaseEntity):
    id: str = Field(description="Binding row id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Binding lifecycle")

    inbound_ticket: Annotated[
        AssociationOne[ClinicalInboundShipmentTicketEntity],
        NoInverse(),
    ] = Rel(description="Subject inbound lot")  # type: ignore[assignment]

    transport_anchor: Annotated[
        AssociationOne[ClinicalTransportAnchorEntity],
        NoInverse(),
    ] = Rel(description="Chosen modality snapshot")  # type: ignore[assignment]


ClinicalInboundTransportBindingEntity.model_rebuild()
