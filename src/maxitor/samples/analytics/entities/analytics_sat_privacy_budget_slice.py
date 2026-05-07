# src/maxitor/samples/analytics/entities/analytics_sat_privacy_budget_slice.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle


@entity(description="Privacy budget ledger slice isolated as its own subgraph root", domain=AnalyticsDomain)
class PrivacyBudgetSliceEntity(BaseEntity):
    lifecycle: AnalyticsFactLifecycle = Field(description="Privacy slice lifecycle")
    id: str = Field(description="Slice id")


PrivacyBudgetSliceEntity.model_rebuild()
