# src/maxitor/samples/store/entities/store_line_warranty_offer.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderLineEntity


@entity(description="Warranty facet on catalog line", domain=StoreDomain)
class WarrantyOfferFacetEntity(BaseEntity):
    id: str = Field(description="WarrantyOfferFacetEntity id")
    lifecycle: SalesOrderLineLifecycle = Field(description="WarrantyOfferFacetEntity lifecycle")

    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Owning order line anchor")  # type: ignore[assignment]


WarrantyOfferFacetEntity.model_rebuild()
