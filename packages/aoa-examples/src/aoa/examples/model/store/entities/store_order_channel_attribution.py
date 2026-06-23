# packages/aoa-examples/src/aoa/examples/model/store/entities/store_order_channel_attribution.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.store.entities.sales_core import SalesOrderEntity
from aoa.examples.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.examples.model.store.store_domain import StoreDomain


@entity(description="Order channel attribution facet", domain=StoreDomain)
class OrderChannelAttributionEntity(BaseEntity):
    id: str = Field(description="OrderChannelAttributionEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="OrderChannelAttributionEntity lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(
        description="Parent sales order anchor"
    )  # type: ignore[assignment]


OrderChannelAttributionEntity.model_rebuild()
