# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_regulatory_ptr.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.arbitration_brief_stub import ArbitrationBriefStubCoreEntity
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Regulatory submission pointer chained from arbitration brief stub", domain=BillingDomain)
class RegulatorySubmissionPointerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Pointer id")
    lifecycle: BillingDenseLifecycle = Field(description="Regulatory pointer lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    brief: Annotated[
        AssociationOne[ArbitrationBriefStubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Upstream arbitration artefact"
    )

    regulator_code: str = Field(description="Regulator identifier")
    submission_channel: str = Field(description="Portal or batch channel code")
    external_case_id: str = Field(description="Downstream regulator ticket id")
    submitted_at_iso: str = Field(description="Submission timestamp (UTC)")


RegulatorySubmissionPointerCoreEntity.model_rebuild()
