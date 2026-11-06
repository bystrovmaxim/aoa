# packages/aoa-demo/src/aoa/demo/model/analytics/resources/storage.py
"""AnalyticsStorage — the store that holds the analytics domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.analytics.domain import AnalyticsDomain
from aoa.demo.model.data_sources.analytics_data_source import AnalyticsDataSource


@meta(description="Stores the analytics model (stub)", domain=AnalyticsDomain)
class AnalyticsStorage(BaseStorage[AnalyticsDataSource]):
    """Hold the analytics domain's entities; the demo never opens it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
