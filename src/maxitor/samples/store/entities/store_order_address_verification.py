# src/maxitor/samples/store/entities/store_order_address_verification.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import CustomerAccountEntity


@entity(description="Address verification keyed to customer profile subgraph", domain=StoreDomain)
class AddressVerificationTrailEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="AV verification lifecycle")
    id: str = Field(description="Verification id")

    customer: Annotated[
        AssociationOne[CustomerAccountEntity],
        NoInverse(),
    ] = Rel(description="Parent customer aggregate")  # type: ignore[assignment]


AddressVerificationTrailEntity.model_rebuild()
