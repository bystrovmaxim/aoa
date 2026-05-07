# src/maxitor/samples/store/entities/payment_capture.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Payment capture row", domain=StoreDomain)
class PaymentCaptureEntity(BaseEntity):
    id: str = Field(description="Capture id")
    lifecycle: SalesOrderLifecycle = Field(description="Capture lifecycle")
    amount: float = Field(description="Captured amount", ge=0)
    captured_at: str = Field(description="Capture timestamp")

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Captured order")  # type: ignore[assignment]


PaymentCaptureEntity.model_rebuild()
