# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/store_order_shipment_estimate.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(description="Shipment ETA heuristic hanging off parcels instead of repeating order centroid", domain=StoreDomain)
class ShipmentEstimateEntity(BaseEntity):
    id: str = Field(description="Estimate id")
    lifecycle: SalesOrderLifecycle = Field(description="Estimate lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Parent parcel artefact")  # type: ignore[assignment]


ShipmentEstimateEntity.model_rebuild()
