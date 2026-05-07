# src/maxitor/samples/analytics/entities/analytics_mesh_rollup_privacy.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_metric_rollup_staging import AnalyticsMetricRollupStagingEntity
from maxitor.samples.analytics.entities.analytics_sat_privacy_budget_slice import PrivacyBudgetSliceEntity


@entity(description="Associates heavyweight rollup egress with sovereign privacy budgeting island", domain=AnalyticsDomain)
class AnalyticsRollupPrivacyCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlator id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Correlator lifecycle")

    rollup_staging: Annotated[
        AssociationOne[AnalyticsMetricRollupStagingEntity],
        NoInverse(),
    ] = Rel(description="Rollup staging anchor")  # type: ignore[assignment]

    privacy_slice: Annotated[
        AssociationOne[PrivacyBudgetSliceEntity],
        NoInverse(),
    ] = Rel(description="Isolated privacy budget anchor")  # type: ignore[assignment]


AnalyticsRollupPrivacyCorrelateEntity.model_rebuild()
