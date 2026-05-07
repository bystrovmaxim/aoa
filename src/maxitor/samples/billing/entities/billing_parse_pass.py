# src/maxitor/samples/billing/entities/billing_parse_pass.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingPipelineLifecycle
from maxitor.samples.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestEntity


@entity(description="Parse pass artifact on ingest manifest", domain=BillingDomain)
class BillingParsePassEntity(BaseEntity):
    lifecycle: BillingPipelineLifecycle = Field(description="Parse lifecycle")
    id: str = Field(description="Parse pass id")

    manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Source manifest")  # type: ignore[assignment]

    fx_residual_tag: Annotated[
        AssociationOne["FxResidualTagEntity"],  # noqa: F821, UP037
        NoInverse(),
    ] = Rel(description="FX residual tag linked to this parse pass")  # type: ignore[assignment]

    retrieval_evidence_bundle: Annotated[
        AssociationOne["RetrievalEvidenceBundleEntity"],  # noqa: F821, UP037
        NoInverse(),
    ] = Rel(description="Retrieval evidence bundle associated with parse outcome")  # type: ignore[assignment]

    parser_semver: str = Field(description="Parser implementation semantic version")
    pass_sequence_no: int = Field(description="Monotonic retry index for same manifest hash", ge=0)
    diagnostics_uri: str = Field(description="Pointer to diagnostics bundle")
    wallclock_elapsed_ms: int = Field(description="Observed ingest duration milliseconds", ge=0)
