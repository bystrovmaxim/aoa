# src/maxitor/samples/analytics/entities/analytics_sat_data_quality_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.analytics.domain import AnalyticsDomain
from maxitor.samples.analytics.entities.an_dense_lifecycle import AnalyticsFactLifecycle
from maxitor.samples.analytics.entities.analytics_sat_experiment_overlay import ExperimentOverlayEntity


@entity(description="DQ ticket continuing experiment-overlay chain segment", domain=AnalyticsDomain)
class DataQualityTicketEntity(BaseEntity):
    id: str = Field(description="Ticket id")
    lifecycle: AnalyticsFactLifecycle = Field(description="DQ ticket lifecycle")

    experiment_overlay: Annotated[
        AssociationOne[ExperimentOverlayEntity],
        NoInverse(),
    ] = Rel(description="Upstream overlay facet")  # type: ignore[assignment]


DataQualityTicketEntity.model_rebuild()
