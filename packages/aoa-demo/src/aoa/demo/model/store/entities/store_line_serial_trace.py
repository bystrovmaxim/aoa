# packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_serial_trace.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_core import SalesOrderLineDetailEntity
from aoa.demo.model.store.entities.sales_order_line_lifecycle import SalesOrderLineLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Serialized lot linkage on line", domain=StoreDomain)
class LineSerialLotTraceCoreEntity(BaseCoreEntity):
    id: str = Field(description="LineSerialLotTraceCoreEntity id")
    lifecycle: SalesOrderLineLifecycle = Field(description="LineSerialLotTraceCoreEntity lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order_line: Annotated[
        AssociationOne[SalesOrderLineDetailEntity],
        NoInverse(),
    ] = Field(
        description="Owning order line anchor"
    )


LineSerialLotTraceCoreEntity.model_rebuild()
