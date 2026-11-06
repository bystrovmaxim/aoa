# packages/aoa-demo/src/aoa/demo/model/store/entities/store_cart_merge_trace.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.storefront_session_lifecycle import StorefrontSessionLifecycle
from aoa.demo.model.store.resources.storefront_session_cache_storage import StorefrontSessionCacheStorage


@entity(description="Cart merge diagnostics hanging off buyer profile graph", resource=StorefrontSessionCacheStorage)
class CartMergeTraceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Trace id")
    lifecycle: StorefrontSessionLifecycle = Field(description="Merge trace lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")


CartMergeTraceCoreEntity.model_rebuild()
