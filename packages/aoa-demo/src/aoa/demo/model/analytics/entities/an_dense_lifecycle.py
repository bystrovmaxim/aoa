# packages/aoa-demo/src/aoa/demo/model/analytics/entities/an_dense_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class AnalyticsPipelineStateEntity(BaseStateEntity):
    """Status of the AnalyticsPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    INGEST = value(code="ingest", display_name="Ingest", sort_order=1)
    HYDRATE = value(code="hydrate", display_name="Hydrate", sort_order=2)
    COMMIT = value(code="commit", display_name="Committed", sort_order=3)



class AnalyticsPipelineLifecycle(Lifecycle[AnalyticsPipelineStateEntity]):
    """ingest phases for linear spine."""


    _template = (
        Lifecycle().state(AnalyticsPipelineStateEntity.INGEST).to(AnalyticsPipelineStateEntity.HYDRATE).initial().state(AnalyticsPipelineStateEntity.HYDRATE).to(AnalyticsPipelineStateEntity.COMMIT).intermediate().state(AnalyticsPipelineStateEntity.COMMIT).final()
    )


class AnalyticsFactStateEntity(BaseStateEntity):
    """Status of the AnalyticsFact axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    INDEXED = value(code="indexed", display_name="Indexed", sort_order=2)
    FROZEN = value(code="frozen", display_name="Frozen", sort_order=3)



class AnalyticsFactLifecycle(Lifecycle[AnalyticsFactStateEntity]):
    """wide hub satellites."""


    _template = (
        Lifecycle().state(AnalyticsFactStateEntity.OPEN).to(AnalyticsFactStateEntity.INDEXED).initial().state(AnalyticsFactStateEntity.INDEXED).to(AnalyticsFactStateEntity.FROZEN).intermediate().state(AnalyticsFactStateEntity.FROZEN).final()
    )
