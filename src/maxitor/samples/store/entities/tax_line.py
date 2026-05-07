# src/maxitor/samples/store/entities/tax_line.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Tax line row", domain=StoreDomain)
class TaxLineEntity(BaseEntity):
    lifecycle: SalesOrderLifecycle = Field(description="Tax line lifecycle")
    id: str = Field(description="Tax line id")
    tax_code: str = Field(description="Tax code")
    tax_amount: float = Field(description="Tax amount", ge=0)

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Taxed order")  # type: ignore[assignment]


TaxLineEntity.model_rebuild()
