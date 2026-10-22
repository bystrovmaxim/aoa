# packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_line_parcel_pick.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_core import SalesOrderLineDetailEntity
from aoa.demo.model.store.entities.sales_order_line_lifecycle import SalesOrderLineLifecycle
from aoa.demo.model.store.entities.shipment_parcel import ShipmentParcelCoreEntity
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Warehouse pick linkage between order lines and heterogeneous parcel batches", domain=StoreDomain)
class StoreLineParcelPickCoreEntity(BaseCoreEntity):
    id: str = Field(description="Pick id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Pick lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order_line: Annotated[
        AssociationOne[SalesOrderLineDetailEntity],
        NoInverse(),
    ] = Rel(
        description="Fulfilling order line artefact"
    )  # type: ignore[assignment]

    parcel: Annotated[
        AssociationOne[ShipmentParcelCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Target parcel artefact"
    )  # type: ignore[assignment]


StoreLineParcelPickCoreEntity.model_rebuild()
