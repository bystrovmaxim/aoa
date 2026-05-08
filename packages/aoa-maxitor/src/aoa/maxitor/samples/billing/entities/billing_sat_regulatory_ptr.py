# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_sat_regulatory_ptr.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.arbitration_brief_stub import ArbitrationBriefStubEntity
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Regulatory submission pointer chained from arbitration brief stub", domain=BillingDomain)
class RegulatorySubmissionPointerEntity(BaseEntity):
    id: str = Field(description="Pointer id")
    lifecycle: BillingDenseLifecycle = Field(description="Regulatory pointer lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    brief: Annotated[
        AssociationOne[ArbitrationBriefStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream arbitration artefact")  # type: ignore[assignment]

    regulator_code: str = Field(description="Regulator identifier")
    submission_channel: str = Field(description="Portal or batch channel code")
    external_case_id: str = Field(description="Downstream regulator ticket id")
    submitted_at_iso: str = Field(description="Submission timestamp (UTC)")


RegulatorySubmissionPointerEntity.model_rebuild()
