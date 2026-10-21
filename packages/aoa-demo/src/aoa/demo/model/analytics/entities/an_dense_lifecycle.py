# packages/aoa-demo/src/aoa/demo/model/analytics/entities/an_dense_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class AnalyticsPipelineStateEntity(BaseStateEntity):
    """Status of the AnalyticsPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class AnalyticsPipelineLifecycle(Lifecycle, StateVocabulary):
    """ingest phases for linear spine."""

    INGEST = AnalyticsPipelineStateEntity(code="ingest", display_name="Ingest", sort_order=1)
    HYDRATE = AnalyticsPipelineStateEntity(code="hydrate", display_name="Hydrate", sort_order=2)
    COMMIT = AnalyticsPipelineStateEntity(code="commit", display_name="Committed", sort_order=3)

    _template = (
        Lifecycle().state(INGEST).to(HYDRATE).initial().state(HYDRATE).to(COMMIT).intermediate().state(COMMIT).final()
    )


class AnalyticsFactStateEntity(BaseStateEntity):
    """Status of the AnalyticsFact axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class AnalyticsFactLifecycle(Lifecycle, StateVocabulary):
    """wide hub satellites."""

    OPEN = AnalyticsFactStateEntity(code="open", display_name="Open", sort_order=1)
    INDEXED = AnalyticsFactStateEntity(code="indexed", display_name="Indexed", sort_order=2)
    FROZEN = AnalyticsFactStateEntity(code="frozen", display_name="Frozen", sort_order=3)

    _template = (
        Lifecycle().state(OPEN).to(INDEXED).initial().state(INDEXED).to(FROZEN).intermediate().state(FROZEN).final()
    )
