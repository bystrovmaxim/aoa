# src/maxitor/samples/store/entities/store_order_fraud_challenge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Step-up fraud challenge", domain=StoreDomain)
class FraudChallengeTicketEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="FraudChallengeTicketEntity lifecycle")
    id: str = Field(description="FraudChallengeTicketEntity id")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


FraudChallengeTicketEntity.model_rebuild()
