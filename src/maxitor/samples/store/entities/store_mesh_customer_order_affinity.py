# src/maxitor/samples/store/entities/store_mesh_customer_order_affinity.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import CustomerAccountEntity, SalesOrderEntity


@entity(description="Many-to-many style affinity row bridging buyer subgraph and transactional orders", domain=StoreDomain)
class StoreCustomerOrderAffinityEntity(BaseEntity):
    id: str = Field(description="Affinity id")
    lifecycle: SalesOrderLifecycle = Field(description="Affinity lifecycle")

    customer: Annotated[
        AssociationOne[CustomerAccountEntity],
        NoInverse(),
    ] = Rel(description="Buyer profile anchor")  # type: ignore[assignment]

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Order aggregate anchor")  # type: ignore[assignment]


StoreCustomerOrderAffinityEntity.model_rebuild()
