# src/maxitor/samples/analytics/entities/an_dense_lifecycle.py
from action_machine.domain import Lifecycle


class AnalyticsPipelineLifecycle(Lifecycle):
    """ingest phases for linear spine."""

    _template = (
        Lifecycle()
        .state("ingest", "Ingest").to("hydrate").initial()
        .state("hydrate", "Hydrate").to("commit").intermediate()
        .state("commit", "Committed").final()
    )


class AnalyticsFactLifecycle(Lifecycle):
    """wide hub satellites."""

    _template = (
        Lifecycle()
        .state("open", "Open").to("indexed").initial()
        .state("indexed", "Indexed").to("frozen").intermediate()
        .state("frozen", "Frozen").final()
    )
