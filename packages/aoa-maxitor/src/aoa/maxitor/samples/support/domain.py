# packages/aoa-maxitor/src/aoa/maxitor/samples/support/domain.py
"""Bounded-context marker for support — demo ``@depends`` on other actions."""

from aoa.action_machine.domain import BaseDomain


class SupportDomain(BaseDomain):
    name = "support"
    description = "Sample slice for action-to-action @depends (same and cross domain)"
