# src/maxitor/samples/clinical_supply/entities/cs_inbound_shipment_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_consumable_sku_row import ClinicalConsumableSkuEntity
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_packing_anchor import ClinicalPackingAnchorEntity
from maxitor.samples.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubEntity


@entity(
    description="Inbound partner lot keyed to SKU and packing posture (supply row analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalInboundShipmentTicketEntity(BaseEntity):
    lifecycle: ClinicalSupplyLifecycle = Field(description="Inbound ticket lifecycle")
    id: str = Field(description="Inbound ticket id")

    partner_hub: Annotated[
        AssociationOne[ClinicalPartnerHubEntity],
        NoInverse(),
    ] = Rel(description="Fulfillment partner")  # type: ignore[assignment]

    consumable_row: Annotated[
        AssociationOne[ClinicalConsumableSkuEntity],
        NoInverse(),
    ] = Rel(description="Shipped SKU master")  # type: ignore[assignment]

    packing_anchor: Annotated[
        AssociationOne[ClinicalPackingAnchorEntity],
        NoInverse(),
    ] = Rel(description="Lot packing profile")  # type: ignore[assignment]


ClinicalInboundShipmentTicketEntity.model_rebuild()
