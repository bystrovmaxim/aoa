# packages/aoa-demo/src/aoa/demo/model/analytics/entities/an_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class AnalyticsPipelineStateEntity(BaseStateEntity):
    """Status of the AnalyticsPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    INGEST = AnalyticsPipelineStateEntity(code="ingest", display_name="Ingest", sort_order=1)  # noqa: F821
    HYDRATE = AnalyticsPipelineStateEntity(code="hydrate", display_name="Hydrate", sort_order=2)  # noqa: F821
    COMMIT = AnalyticsPipelineStateEntity(code="commit", display_name="Committed", sort_order=3)  # noqa: F821



class AnalyticsPipelineLifecycle(Lifecycle[AnalyticsPipelineStateEntity]):
    """ingest phases for linear spine."""


    _template = (
        Lifecycle().state(AnalyticsPipelineStateEntity.INGEST).to(AnalyticsPipelineStateEntity.HYDRATE).initial().state(AnalyticsPipelineStateEntity.HYDRATE).to(AnalyticsPipelineStateEntity.COMMIT).intermediate().state(AnalyticsPipelineStateEntity.COMMIT).final()
    )


class AnalyticsFactStateEntity(BaseStateEntity):
    """Status of the AnalyticsFact axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = AnalyticsFactStateEntity(code="open", display_name="Open", sort_order=1)  # noqa: F821
    INDEXED = AnalyticsFactStateEntity(code="indexed", display_name="Indexed", sort_order=2)  # noqa: F821
    FROZEN = AnalyticsFactStateEntity(code="frozen", display_name="Frozen", sort_order=3)  # noqa: F821



class AnalyticsFactLifecycle(Lifecycle[AnalyticsFactStateEntity]):
    """wide hub satellites."""


    _template = (
        Lifecycle().state(AnalyticsFactStateEntity.OPEN).to(AnalyticsFactStateEntity.INDEXED).initial().state(AnalyticsFactStateEntity.INDEXED).to(AnalyticsFactStateEntity.FROZEN).intermediate().state(AnalyticsFactStateEntity.FROZEN).final()
    )
