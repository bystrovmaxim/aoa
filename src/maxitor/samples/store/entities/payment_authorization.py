# src/maxitor/samples/store/entities/payment_authorization.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Payment authorization row", domain=StoreDomain)
class PaymentAuthorizationEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Authorization lifecycle")
    id: str = Field(description="Authorization id")
    provider: str = Field(description="PSP name")
    approved_amount: float = Field(description="Approved amount", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Authorized order")  # type: ignore[assignment]


PaymentAuthorizationEntity.model_rebuild()
