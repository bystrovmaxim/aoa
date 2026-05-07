# src/maxitor/samples/billing/entities/billing_sat_duplicate_ledger.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_parse_pass import BillingParsePassEntity


@entity(description="Duplicate suppression fragment attached to parse pass", domain=BillingDomain)
class DuplicateSuppressionLedgerEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Duplicate ledger lifecycle")
    id: str = Field(description="Ledger fragment id")

    parse_pass: Annotated[
        AssociationOne[BillingParsePassEntity],
        NoInverse(),
    ] = Rel(description="Owning parse pass")  # type: ignore[assignment]

    suppression_scope: str = Field(description="Scope key (merchant, MID, PAN prefix)")
    fingerprint_hex: str = Field(description="Payload fingerprint sampled for duplicate probes")
    collision_count: int = Field(description="Collisions suppressed in-batch", ge=0)
    last_collision_at_iso: str = Field(description="Last suppressed duplicate occurrence (UTC)")


DuplicateSuppressionLedgerEntity.model_rebuild()
