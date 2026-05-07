# src/maxitor/samples/inventory/entities/inv_recall_signal.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.inventory.domain import InventoryDomain
from maxitor.samples.inventory.entities.inv_dense_lifecycle import InvDenseLifecycle
from maxitor.samples.inventory.entities.inv_disposition_advice import DispositionAdviceEntity


@entity(description="Recall signal extending disposition segment", domain=InventoryDomain)
class RecallSignalEntity(BaseEntity):
    id: str = Field(description="Signal id")
    lifecycle: InvDenseLifecycle = Field(description="Recall lifecycle")

    disposition: Annotated[
        AssociationOne[DispositionAdviceEntity],
        NoInverse(),
    ] = Rel(description="Owning disposition artefact")  # type: ignore[assignment]


RecallSignalEntity.model_rebuild()
