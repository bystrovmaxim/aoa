# packages/aoa-maxitor/src/aoa/maxitor/model/app_view/app_view_domain.py
"""Bounded-context marker for root app-view orchestration."""

from aoa.action_machine.domain import BaseDomain


class AppViewDomain(BaseDomain):
    name = "app_view"
    description = "Root app-view composition: sidebar menu, diagrams, entities, and ERD rows"
