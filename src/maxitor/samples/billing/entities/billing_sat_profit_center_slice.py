# src/maxitor/samples/billing/entities/billing_sat_profit_center_slice.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestEntity


@entity(description="Profit-center split hanging off ingest manifest root", domain=BillingDomain)
class ProfitCenterContributionEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Profit center lifecycle")
    id: str = Field(description="Slice id")

    ingest_manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Owning ingest manifest")  # type: ignore[assignment]


ProfitCenterContributionEntity.model_rebuild()
