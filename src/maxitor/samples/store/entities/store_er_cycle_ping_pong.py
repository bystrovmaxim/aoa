# src/maxitor/samples/store/entities/store_er_cycle_ping_pong.py
"""
Artificial mutual ``AssociationOne`` pair for ERD cyclic-FK demos (store domain).

``Inverse`` pairing closes a **two-node** interchange cycle. One-way anchors (``NoInverse``)
into :class:`~maxitor.samples.store.entities.sales_core.CustomerAccountEntity` and
:class:`~maxitor.samples.store.entities.sales_core.SalesOrderEntity` merge the subgraph with
the main storefront spine in a single interchange component.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, Inverse, Lifecycle, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.sales_core import CustomerAccountEntity, SalesOrderEntity


class _StoreDirectedCycleSketchLifecycle(Lifecycle):
    _template = Lifecycle().state("open", "Open").to("settled").initial().state("settled", "Settled").final()


@entity(
    description="Ping side of mutual FK skeleton (two-node interchange cycle demo)",
    domain=StoreDomain,
)
class StoreDirectedCyclePingEntity(BaseEntity):
    id: str = Field(description="Ping row id")
    lifecycle: _StoreDirectedCycleSketchLifecycle = Field(description="Ping sketch lifecycle")

    pong_peer: Annotated[
        AssociationOne[StoreDirectedCyclePongEntity],
        Inverse(StoreDirectedCyclePongEntity, "ping_peer"),
    ] = Rel(description="Points at pong counterpart; closes a 2-node cycle")  # type: ignore[assignment]

    storefront_customer_anchor: Annotated[
        AssociationOne[CustomerAccountEntity],
        NoInverse(),
    ] = Rel(
        description="Sample FK tying the ping row into core customer/order graph (no reciprocal field)",
    )  # type: ignore[assignment]


@entity(
    description="Pong side of mutual FK skeleton (two-node interchange cycle demo)",
    domain=StoreDomain,
)
class StoreDirectedCyclePongEntity(BaseEntity):
    id: str = Field(description="Pong row id")
    lifecycle: _StoreDirectedCycleSketchLifecycle = Field(description="Pong sketch lifecycle")

    ping_peer: Annotated[
        AssociationOne[StoreDirectedCyclePingEntity],
        Inverse(StoreDirectedCyclePingEntity, "pong_peer"),
    ] = Rel(description="Points at ping counterpart; completes mutual reference")  # type: ignore[assignment]

    storefront_order_anchor: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(
        description="Sample FK tying the pong row into the sales-order spine (no reciprocal field)",
    )  # type: ignore[assignment]


StoreDirectedCyclePingEntity.model_rebuild()
StoreDirectedCyclePongEntity.model_rebuild()
