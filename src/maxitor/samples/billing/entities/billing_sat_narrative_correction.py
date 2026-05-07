# src/maxitor/samples/billing/entities/billing_sat_narrative_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_canonical_row_artifact import BillingCanonicalRowArtifactEntity
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Narrative correction attached to canonical ingest row", domain=BillingDomain)
class NarrativeCorrectionEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Correction lifecycle")
    id: str = Field(description="Row id")

    canonical_row: Annotated[
        AssociationOne[BillingCanonicalRowArtifactEntity],
        NoInverse(),
    ] = Rel(description="Parent canonical ingest artifact")  # type: ignore[assignment]


NarrativeCorrectionEntity.model_rebuild()
