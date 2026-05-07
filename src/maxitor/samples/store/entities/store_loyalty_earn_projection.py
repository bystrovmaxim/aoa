# src/maxitor/samples/store/entities/store_loyalty_earn_projection.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle


@entity(description="Loyalty earn projection keyed off invoicing artefacts (distinct from header mesh)", domain=StoreDomain)
class LoyaltyEarnProjectionEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Projection lifecycle")
    id: str = Field(description="Projection id")

    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Owning invoice artefact")  # type: ignore[assignment]


LoyaltyEarnProjectionEntity.model_rebuild()
