# src/maxitor/samples/billing/entities/arbitration_brief_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_acquirer_integrity import AcquirerIntegrityCheckEntity


@entity(description="Arbitration brief following acquirer integrity checkpoint", domain=BillingDomain)
class ArbitrationBriefStubEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Brief lifecycle")
    id: str = Field(description="Brief id")

    integrity_checkpoint: Annotated[
        AssociationOne[AcquirerIntegrityCheckEntity],
        NoInverse(),
    ] = Rel(description="Upstream acquirer integrity artefact")  # type: ignore[assignment]


ArbitrationBriefStubEntity.model_rebuild()
