# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_duplicate_ledger.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_parse_pass import BillingParsePassCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Duplicate suppression fragment attached to parse pass", domain=BillingDomain)
class DuplicateSuppressionLedgerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Ledger fragment id")
    lifecycle: BillingDenseLifecycle = Field(description="Duplicate ledger lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    parse_pass: Annotated[
        AssociationOne[BillingParsePassCoreEntity],
        NoInverse(),
    ] = Field(
        description="Owning parse pass"
    )

    suppression_scope: str = Field(description="Scope key (merchant, MID, PAN prefix)")
    fingerprint_hex: str = Field(description="Payload fingerprint sampled for duplicate probes")
    collision_count: int = Field(description="Collisions suppressed in-batch", ge=0)
    last_collision_at_iso: str = Field(description="Last suppressed duplicate occurrence (UTC)")


DuplicateSuppressionLedgerCoreEntity.model_rebuild()
