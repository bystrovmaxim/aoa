# packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_inbound_shipment_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.clinical_supply.domain import ClinicalSupplyDomain
from aoa.demo.model.clinical_supply.entities.cs_consumable_sku_row import ClinicalConsumableSkuCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from aoa.demo.model.clinical_supply.entities.cs_packing_anchor import ClinicalPackingAnchorCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubCoreEntity


@entity(
    description="Inbound partner lot keyed to SKU and packing posture (supply row analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalInboundShipmentTicketCoreEntity(BaseCoreEntity):
    id: str = Field(description="Inbound ticket id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="Inbound ticket lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    partner_hub: Annotated[
        AssociationOne[ClinicalPartnerHubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Fulfillment partner"
    )

    consumable_row: Annotated[
        AssociationOne[ClinicalConsumableSkuCoreEntity],
        NoInverse(),
    ] = Field(
        description="Shipped SKU master"
    )

    packing_anchor: Annotated[
        AssociationOne[ClinicalPackingAnchorCoreEntity],
        NoInverse(),
    ] = Field(
        description="Lot packing profile"
    )


ClinicalInboundShipmentTicketCoreEntity.model_rebuild()
