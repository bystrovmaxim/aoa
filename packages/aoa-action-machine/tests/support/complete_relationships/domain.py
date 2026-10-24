# packages/aoa-action-machine/tests/support/complete_relationships/domain.py
"""The shared domain for the two-module reciprocal relationship fixtures."""

from aoa.action_machine.domain import BaseDomain


class CrossDomain(BaseDomain):
    """Domain both declaration modules belong to."""

    name = "cross"
    description = "Cross-module"
