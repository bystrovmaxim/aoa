# packages/aoa-demo/src/aoa/demo/model/store/entities/store_er_cycle_ping_pong.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""
Artificial mutual ``AssociationOne`` pair for ERD cyclic-FK demos (store domain).

``Inverse`` pairing closes a **two-node** interchange cycle. One-way anchors (``NoInverse``)
into :class:`~aoa.demo.model.store.entities.sales_core.CustomerAccountCoreEntity` and
:class:`~aoa.demo.model.store.entities.sales_core.SalesOrderCoreEntity` merge the subgraph with
the main storefront spine in a single interchange component.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseStateEntity,
    Inverse,
    Lifecycle,
    NoInverse,
    Rel,
    value,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_core import CustomerAccountCoreEntity, SalesOrderCoreEntity
from aoa.demo.model.store.store_domain import StoreDomain


class _StoreDirectedCycleSketchStateEntity(BaseStateEntity):
    """Status of the _StoreDirectedCycleSketch axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    SETTLED = value(code="settled", display_name="Settled", sort_order=2)



class _StoreDirectedCycleSketchLifecycle(Lifecycle[_StoreDirectedCycleSketchStateEntity]):
    """Statuses and links of the _StoreDirectedCycleSketchLifecycle axis."""


    _template = Lifecycle().state(_StoreDirectedCycleSketchStateEntity.OPEN).to(_StoreDirectedCycleSketchStateEntity.SETTLED).initial().state(_StoreDirectedCycleSketchStateEntity.SETTLED).final()


@entity(
    description="Ping side of mutual FK skeleton (two-node interchange cycle demo)",
    domain=StoreDomain,
)
class StoreDirectedCyclePingCoreEntity(BaseCoreEntity):
    id: str = Field(description="Ping row id")
    lifecycle: _StoreDirectedCycleSketchLifecycle = Field(description="Ping sketch lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    pong_peer: Annotated[
        AssociationOne[StoreDirectedCyclePongCoreEntity],
        Inverse(StoreDirectedCyclePongCoreEntity, "ping_peer"),
    ] = Rel(
        description="Points at pong counterpart; closes a 2-node cycle"
    )  # type: ignore[assignment]

    storefront_customer_anchor: Annotated[
        AssociationOne[CustomerAccountCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Sample FK tying the ping row into core customer/order graph (no reciprocal field)",
    )  # type: ignore[assignment]


@entity(
    description="Pong side of mutual FK skeleton (two-node interchange cycle demo)",
    domain=StoreDomain,
)
class StoreDirectedCyclePongCoreEntity(BaseCoreEntity):
    id: str = Field(description="Pong row id")
    lifecycle: _StoreDirectedCycleSketchLifecycle = Field(description="Pong sketch lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    ping_peer: Annotated[
        AssociationOne[StoreDirectedCyclePingCoreEntity],
        Inverse(StoreDirectedCyclePingCoreEntity, "pong_peer"),
    ] = Rel(
        description="Points at ping counterpart; completes mutual reference"
    )  # type: ignore[assignment]

    storefront_order_anchor: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Sample FK tying the pong row into the sales-order spine (no reciprocal field)",
    )  # type: ignore[assignment]


StoreDirectedCyclePingCoreEntity.model_rebuild()
StoreDirectedCyclePongCoreEntity.model_rebuild()
