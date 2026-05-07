# src/maxitor/samples/analytics/entities/analytics_sat_budgeted_query_plan.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsPipelineLifecycle
from maxitor.samples.analytics.entities.analytics_sampling_policy import AnalyticsSamplingPolicyEntity


@entity(description="Budgeted interactive query facet on sampling policy branch", domain=AnalyticsDomain)
class BudgetedQueryPlanEntity(BaseEntity):
    id: str = Field(description="Plan id")
    lifecycle: AnalyticsPipelineLifecycle = Field(description="Budget plan lifecycle")

    sampling_policy: Annotated[
        AssociationOne[AnalyticsSamplingPolicyEntity],
        NoInverse(),
    ] = Rel(description="Owning sampling policy")  # type: ignore[assignment]


BudgetedQueryPlanEntity.model_rebuild()
