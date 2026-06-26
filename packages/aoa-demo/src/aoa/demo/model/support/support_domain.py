# packages/aoa-demo/src/aoa/demo/model/support/support_domain.py
"""Bounded-context marker for support — demo ``@depends`` on other actions."""

from aoa.action_machine.domain import BaseDomain


class SupportDomain(BaseDomain):
    name = "support"
    description = "Sample slice for action-to-action @depends (same and cross domain)"
