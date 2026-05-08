# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_inbound_shipment_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_consumable_sku_row import ClinicalConsumableSkuEntity
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from aoa.maxitor.samples.clinical_supply.entities.cs_packing_anchor import ClinicalPackingAnchorEntity
from aoa.maxitor.samples.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubEntity


@entity(
    description="Inbound partner lot keyed to SKU and packing posture (supply row analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalInboundShipmentTicketEntity(BaseEntity):
    id: str = Field(description="Inbound ticket id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Inbound ticket lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
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
