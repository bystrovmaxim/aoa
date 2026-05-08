# src/maxitor/samples/store/entities/store_mesh_order_parcel_handoff.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity
from maxitor.samples.store.entities.shipment_parcel import ShipmentParcelEntity


@entity(
    description="Junction aligning header orders with parcel fulfilment subgraph (dense mesh cue)",
    domain=StoreDomain,
)
class StoreOrderParcelHandoffEntity(BaseEntity):
    id: str = Field(description="Link id")
    lifecycle: SalesOrderLifecycle = Field(description="Handoff lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Referenced order aggregate")  # type: ignore[assignment]

    parcel: Annotated[
        AssociationOne[ShipmentParcelEntity],
        NoInverse(),
    ] = Rel(description="Referenced shipment parcel artefact")  # type: ignore[assignment]


StoreOrderParcelHandoffEntity.model_rebuild()
