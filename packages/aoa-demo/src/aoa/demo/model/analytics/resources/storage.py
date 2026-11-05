# packages/aoa-demo/src/aoa/demo/model/analytics/resources/storage.py
"""AnalyticsStorage — the store that holds the analytics domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.analytics.domain import AnalyticsDomain


@meta(description="Stores the analytics model (stub)", domain=AnalyticsDomain)
class AnalyticsStorage(BaseStorage):
    """Hold the analytics domain's entities; the demo never opens it."""
