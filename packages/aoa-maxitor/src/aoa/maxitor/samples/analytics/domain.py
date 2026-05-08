# packages/aoa-maxitor/src/aoa/maxitor/samples/analytics/domain.py
"""Bounded-context marker for synthetic telemetry / rollup graph demo."""

from aoa.action_machine.domain import BaseDomain


class AnalyticsDomain(BaseDomain):
    name = "analytics"
    description = "Telemetry ingest + fact correlation hub built for sprawling ERD stress tests"
