# src/maxitor/samples/billing/entities/billing_canonical_row_artifact.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_parse_pass import BillingParsePassEntity


@entity(description="Canonical row emitted from parser", domain=BillingDomain)
class BillingCanonicalRowArtifactEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Row lifecycle")
    id: str = Field(description="Artifact id")

    parse_pass: Annotated[
        AssociationOne[BillingParsePassEntity],
        NoInverse(),
    ] = Rel(description="Originating parse pass")  # type: ignore[assignment]


BillingCanonicalRowArtifactEntity.model_rebuild()
