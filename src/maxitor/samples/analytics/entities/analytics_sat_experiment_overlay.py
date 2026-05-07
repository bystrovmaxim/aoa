# src/maxitor/samples/analytics/entities/analytics_sat_experiment_overlay.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_canonical_telemetry_row import AnalyticsCanonicalTelemetryRowEntity


@entity(description="Experiment overlay anchored on canonical telemetry spine (distinct from ingest branch)", domain=AnalyticsDomain)
class ExperimentOverlayEntity(BaseEntity):
    id: str = Field(description="Overlay id")
    lifecycle: AnalyticsFactLifecycle = Field(description="Experiment overlay lifecycle")

    canonical_row: Annotated[
        AssociationOne[AnalyticsCanonicalTelemetryRowEntity],
        NoInverse(),
    ] = Rel(description="Canonical telemetry lineage parent")  # type: ignore[assignment]


ExperimentOverlayEntity.model_rebuild()
