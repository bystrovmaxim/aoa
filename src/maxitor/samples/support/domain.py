# src/maxitor/samples/support/domain.py
"""Маркер bounded context «support» — демо ``@depends`` на другие actions."""

from action_machine.domain import BaseDomain


class SupportDomain(BaseDomain):
    name = "support"
    description = "Sample slice for action-to-action @depends (same and cross domain)"
