# packages/aoa-demo/src/aoa/demo/model/store/entities/return_request.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.return_request_lifecycle import ReturnRequestLifecycle
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity
from aoa.demo.model.store.resources.storefront_database_storage import StorefrontDatabaseStorage


@entity(description="Return request row", resource=StorefrontDatabaseStorage)
class ReturnRequestCoreEntity(BaseCoreEntity):
    id: str = Field(description="Return request id")
    lifecycle: ReturnRequestLifecycle = Field(description="Return lifecycle")
    reason: str = Field(description="Return reason")
    reason_code: str = Field(default="other", description="Why the customer returns it, as a code: damaged, wrong_item, changed_mind, other")
    exchange_sku: str | None = Field(default=None, description="Product the customer takes instead of a refund; none for a refund")
    status: str = Field(description="Return status")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Field(
        description="Returned order"
    )



ReturnRequestCoreEntity.model_rebuild()
